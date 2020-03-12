# basic text comparison function


def hello_world():
    print("Hello world!")


def text_compare(t1, t2):
    if not t1 and not t2:
        return True
    if t1 == '*' or t2 == '*':
        return True
    return (t1 or '').strip() == (t2 or '').strip()


if __name__ == "__main__":
    hello_world()
