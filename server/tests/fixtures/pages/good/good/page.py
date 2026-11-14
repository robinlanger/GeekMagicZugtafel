from .helper import X


def fetch(options, ctx):
    return {**X, "lang": ctx.lang}
