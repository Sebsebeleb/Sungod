import ast

allowed = [ast.Expression, ast.Num, ast.BinOp, ast.Add, ast.Sub,
           ast.Mult, ast.Div, ast.Pow, ast.BitXor, ast.Add]


def parse(string):
    tree = ast.parse(string, mode='eval')
    nodes = ast.walk(tree)  # Shouldn't this be "climb(tree)" instead?
    if not all((type(i) in allowed for i in nodes)):
        # Evil string, do not allow
        s = "No fishy business allowed here!"
    else:
        s = eval(compile(tree, filename="<ast>", mode="eval"))
    return s
