import ast

allowed = (ast.Num, ast.Str, ast.List, ast.Tuple, ast.Dict, ast.Expression,
           ast.UnaryOp, ast.BinOp, ast.BoolOp, ast.Compare,
           ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is,
           ast.IsNot, ast.In, ast.NotIn,
           ast.UAdd, ast.USub, ast.Not, ast.Invert, ast.Add, ast.Sub,
           ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.LShift,
           ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd, ast.And, ast.Or
           )


def parse(string):
    tree = ast.parse(string, mode='eval')
    nodes = list(ast.walk(tree))  # Shouldn't this be "climb(tree)" instead?
    print nodes
    s = None
    if not all((type(i) in allowed for i in nodes)):
        # Evil string, do not allow
        s = "No fishy business allowed here!"
    return s
