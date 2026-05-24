def on_load(func):
    func._signal_name = "on_load"
    return func

def on_chat_message(func):
    func._signal_name = "on_chat_message"
    return func

def on_follow(func):
    func._signal_name = "on_follow"
    return func