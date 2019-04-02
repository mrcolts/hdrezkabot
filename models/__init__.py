from .serial import Serial
from .message import Message
from .user import User
from .last_update_hash import LastUpdateHash


all_models = [
    Serial, Message, User, LastUpdateHash
]

def init_models(config, loop):
    [loop.run_until_complete(model.init_manager(config)) for model in all_models]
