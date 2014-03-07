import ast

allowed = (ast.Num, ast.Str, ast.List, ast.Tuple, ast.Dict, ast.Expression,
           ast.UnaryOp, ast.BinOp, ast.BoolOp, ast.Compare,
           ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is,
           ast.IsNot, ast.In, ast.NotIn,
           ast.UAdd, ast.USub, ast.Not, ast.Invert, ast.Add, ast.Sub,
           ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.LShift,
           ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd, ast.And, ast.Or
           )


def parse(string, power):
    expr = string
    if power != 0:
        tree = ast.parse(string, mode='eval')
        nodes = list(ast.walk(tree))  # Shouldn't this be "climb(tree)" instead?
        if all((type(i) in allowed for i in nodes)):
            expr = compile(tree, filename="<ast>", mode="eval")
        else:
            expr = None

    if expr:
        import numpy
        expr = eval(expr, {"np":numpy})
    return expr
