"""
Minimal interpreter for a small IEC 61131-3 Structured Text (ST) subset.

Supported: PROGRAM/END_PROGRAM, VAR/VAR_INPUT/VAR_OUTPUT/VAR CONSTANT blocks
declaring BOOL/INT/REAL variables with optional initial values, IF/ELSIF/ELSE/
END_IF, assignment (:=), AND/OR/NOT, comparisons (= <> < <= > >=), + and -,
parentheses, TRUE/FALSE literals, and (* ... *) comments.

This is deliberately NOT a general ST parser -- it implements exactly the
subset needed for the wet-well pump interlock logic in this task.
"""
import re


KEYWORDS = {
    "PROGRAM", "END_PROGRAM", "VAR", "VAR_INPUT", "VAR_OUTPUT", "END_VAR",
    "CONSTANT", "IF", "THEN", "ELSIF", "ELSE", "END_IF", "AND", "OR", "NOT",
    "TRUE", "FALSE", "BOOL", "INT", "REAL",
}

TOKEN_SPEC = [
    ("NUMBER", r"\d+\.\d+|\d+"),
    ("ASSIGN", r":="),
    ("LE", r"<="),
    ("GE", r">="),
    ("NE", r"<>"),
    ("LT", r"<"),
    ("GT", r">"),
    ("EQ", r"="),
    ("COLON", r":"),
    ("SEMI", r";"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("PLUS", r"\+"),
    ("MINUS", r"-"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("SKIP", r"[ \t\r\n]+"),
    ("MISMATCH", r"."),
]

TOKEN_REGEX = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)


class STSyntaxError(Exception):
    pass


def strip_comments(text):
    return re.sub(r"\(\*.*?\*\)", " ", text, flags=re.DOTALL)


def tokenize(text):
    text = strip_comments(text)
    tokens = []
    for m in re.finditer(TOKEN_REGEX, text):
        kind = m.lastgroup
        value = m.group()
        if kind == "SKIP":
            continue
        if kind == "MISMATCH":
            raise STSyntaxError(f"Unexpected character {value!r}")
        if kind == "IDENT" and value.upper() in KEYWORDS:
            kind = value.upper()
            value = value.upper()
        tokens.append((kind, value))
    tokens.append(("EOF", ""))
    return tokens


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def peek_kind(self):
        return self.tokens[self.pos][0]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind):
        tok = self.advance()
        if tok[0] != kind:
            raise STSyntaxError(f"Expected {kind}, got {tok} at position {self.pos}")
        return tok

    # ---- top level ----
    def parse_program(self):
        self.expect("PROGRAM")
        self.expect("IDENT")  # program name, unused
        declarations = {}
        var_input, var_output = [], []
        while self.peek_kind() in ("VAR", "VAR_INPUT", "VAR_OUTPUT"):
            block_kind, decls = self.parse_var_block()
            for name, info in decls.items():
                declarations[name] = info
            if block_kind == "VAR_INPUT":
                var_input.extend(decls.keys())
            elif block_kind == "VAR_OUTPUT":
                var_output.extend(decls.keys())
        statements = self.parse_statement_list({"END_PROGRAM"})
        self.expect("END_PROGRAM")
        return Program(declarations, var_input, var_output, statements)

    def parse_var_block(self):
        block_kind = self.advance()[0]  # VAR / VAR_INPUT / VAR_OUTPUT
        if self.peek_kind() == "CONSTANT":
            self.advance()
        decls = {}
        while self.peek_kind() != "END_VAR":
            name = self.expect("IDENT")[1]
            self.expect("COLON")
            type_tok = self.advance()[0]
            if type_tok not in ("BOOL", "INT", "REAL"):
                raise STSyntaxError(f"Unknown type {type_tok}")
            init = self.default_for_type(type_tok)
            if self.peek_kind() == "ASSIGN":
                self.advance()
                init = self.parse_literal()
            self.expect("SEMI")
            decls[name] = {"type": type_tok, "init": init}
        self.expect("END_VAR")
        if self.peek_kind() == "SEMI":
            self.advance()
        return block_kind, decls

    @staticmethod
    def default_for_type(type_tok):
        return {"BOOL": False, "INT": 0, "REAL": 0.0}[type_tok]

    def parse_literal(self):
        neg = False
        if self.peek_kind() == "MINUS":
            self.advance()
            neg = True
        if self.peek_kind() == "NUMBER":
            raw = self.advance()[1]
            val = float(raw) if "." in raw else int(raw)
            return -val if neg else val
        if self.peek_kind() in ("TRUE", "FALSE"):
            val = self.advance()[0] == "TRUE"
            return val
        raise STSyntaxError(f"Invalid literal at {self.peek()}")

    # ---- statements ----
    def parse_statement_list(self, terminators):
        stmts = []
        while self.peek_kind() not in terminators:
            stmts.append(self.parse_statement())
        return stmts

    def parse_statement(self):
        if self.peek_kind() == "IF":
            return self.parse_if()
        return self.parse_assignment()

    def parse_assignment(self):
        name = self.expect("IDENT")[1]
        self.expect("ASSIGN")
        expr = self.parse_expr()
        self.expect("SEMI")
        return ("assign", name, expr)

    def parse_if(self):
        self.expect("IF")
        cond = self.parse_expr()
        self.expect("THEN")
        body = self.parse_statement_list({"ELSIF", "ELSE", "END_IF"})
        branches = [(cond, body)]
        while self.peek_kind() == "ELSIF":
            self.advance()
            cond2 = self.parse_expr()
            self.expect("THEN")
            body2 = self.parse_statement_list({"ELSIF", "ELSE", "END_IF"})
            branches.append((cond2, body2))
        else_body = []
        if self.peek_kind() == "ELSE":
            self.advance()
            else_body = self.parse_statement_list({"END_IF"})
        self.expect("END_IF")
        if self.peek_kind() == "SEMI":
            self.advance()
        return ("if", branches, else_body)

    # ---- expressions (lowest to highest precedence: OR, AND, NOT, compare, +/-, primary) ----
    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.peek_kind() == "OR":
            self.advance()
            right = self.parse_and()
            left = ("or", left, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek_kind() == "AND":
            self.advance()
            right = self.parse_not()
            left = ("and", left, right)
        return left

    def parse_not(self):
        if self.peek_kind() == "NOT":
            self.advance()
            return ("not", self.parse_not())
        return self.parse_compare()

    def parse_compare(self):
        left = self.parse_add()
        if self.peek_kind() in ("EQ", "NE", "LT", "LE", "GT", "GE"):
            op = self.advance()[0]
            right = self.parse_add()
            return ("cmp", op, left, right)
        return left

    def parse_add(self):
        left = self.parse_term()
        while self.peek_kind() in ("PLUS", "MINUS"):
            op = self.advance()[0]
            right = self.parse_term()
            left = ("arith", op, left, right)
        return left

    def parse_term(self):
        if self.peek_kind() == "MINUS":
            self.advance()
            return ("neg", self.parse_term())
        if self.peek_kind() == "LPAREN":
            self.advance()
            expr = self.parse_expr()
            self.expect("RPAREN")
            return expr
        if self.peek_kind() == "NUMBER":
            raw = self.advance()[1]
            val = float(raw) if "." in raw else int(raw)
            return ("num", val)
        if self.peek_kind() in ("TRUE", "FALSE"):
            val = self.advance()[0] == "TRUE"
            return ("bool", val)
        if self.peek_kind() == "IDENT":
            name = self.advance()[1]
            return ("var", name)
        raise STSyntaxError(f"Unexpected token {self.peek()}")


def eval_expr(node, env):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "bool":
        return node[1]
    if kind == "var":
        if node[1] not in env:
            raise STSyntaxError(f"Undeclared variable {node[1]!r}")
        return env[node[1]]
    if kind == "neg":
        return -eval_expr(node[1], env)
    if kind == "not":
        return not eval_expr(node[1], env)
    if kind == "and":
        return bool(eval_expr(node[1], env)) and bool(eval_expr(node[2], env))
    if kind == "or":
        return bool(eval_expr(node[1], env)) or bool(eval_expr(node[2], env))
    if kind == "cmp":
        op, l, r = node[1], eval_expr(node[2], env), eval_expr(node[3], env)
        return {
            "EQ": l == r, "NE": l != r, "LT": l < r,
            "LE": l <= r, "GT": l > r, "GE": l >= r,
        }[op]
    if kind == "arith":
        op, l, r = node[1], eval_expr(node[2], env), eval_expr(node[3], env)
        return l + r if op == "PLUS" else l - r
    raise STSyntaxError(f"Unknown expression node {node}")


def exec_statements(stmts, env):
    for stmt in stmts:
        if stmt[0] == "assign":
            _, name, expr = stmt
            if name not in env:
                raise STSyntaxError(f"Assignment to undeclared variable {name!r}")
            env[name] = eval_expr(expr, env)
        elif stmt[0] == "if":
            _, branches, else_body = stmt
            for cond, body in branches:
                if eval_expr(cond, env):
                    exec_statements(body, env)
                    break
            else:
                exec_statements(else_body, env)
        else:
            raise STSyntaxError(f"Unknown statement {stmt}")


class Program:
    """A parsed ST program. Call tick(inputs) once per scan cycle."""

    def __init__(self, declarations, var_input, var_output, statements):
        self.declarations = declarations
        self.var_input = var_input
        self.var_output = var_output
        self.statements = statements
        self.env = {name: info["init"] for name, info in declarations.items()}

    @classmethod
    def from_file(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        tokens = tokenize(text)
        parser = Parser(tokens)
        return parser.parse_program()

    def tick(self, inputs):
        for name in self.var_input:
            if name not in inputs:
                raise STSyntaxError(f"Missing required input {name!r}")
            self.env[name] = inputs[name]
        exec_statements(self.statements, self.env)
        return {name: self.env[name] for name in self.var_output}

    def run_sequence(self, ticks):
        """ticks: list of input dicts. Returns list of output dicts, one per tick."""
        return [self.tick(t) for t in ticks]
