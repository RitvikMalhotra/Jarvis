development_mode = False


def enter_development_mode():
    global development_mode
    development_mode = True


def is_development_mode():
    return development_mode
