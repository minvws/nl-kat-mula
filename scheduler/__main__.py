from scheduler import context

if __name__ == "__main__":
    ctx = context.AppContext()

    print(ctx.config)
    print("hello, world")
