from ..lib import commands
from ..lib.constants import KEY_ENTER


class Intent(object):
    help_text = None

    @staticmethod
    def execute(context, arg):
        raise NotImplemented


class PreviousTag(Intent):
    help_text = 'Move to previous tag'

    @staticmethod
    def execute(context, arg):
        active = max(0, context.vars['active_tag'] - 1)
        if context.vars['active_tag'] != active:
            context.vars['active_item'] = 0
            context.vars['active_tag'] = active
            context.adapter.request_state(
                context.model['tags'][active]['name'])


class NextTag(Intent):
    help_text = 'Move to next tag'

    @staticmethod
    def execute(context, arg):
        active = min(len(context.model['tags']) - 1,
                     context.vars['active_tag'] + 1)
        if context.vars['active_tag'] != active:
            context.vars['active_item'] = 0
            context.vars['active_tag'] = active
            context.adapter.request_state(
                context.model['tags'][active]['name'])


class PreviousItem(Intent):
    help_text = 'Move to previous item'

    @staticmethod
    def execute(context, arg):
        context.vars['active_item'] = max(0, context.vars['active_item'] - 1)


class NextItem(Intent):
    help_text = 'Move to next item'

    @staticmethod
    def execute(context, arg):
        context.vars['active_item'] = min(
            len(context.model['items']) - 1,
            context.vars['active_item'] + 1)


class AddItem(Intent):
    help_text = 'Add new item'

    @staticmethod
    def execute(context, arg):
        from . import state
        context.set_state(state.AddStuff())


class Process(Intent):
    help_text = 'Process selected item'

    @staticmethod
    def execute(context, arg):
        if context.vars['active_tag'] == 0 and \
                context.model['tags'][0]['count']:
            from . import state
            context.set_state(state.Process())


class DeleteItem(Intent):
    help_text = 'Delete selected item'

    @staticmethod
    def execute(context, arg):
        if context.model['items']:
            item = context.model['items'][context.vars['active_item']]
            cmd = commands.DeleteItemCommand(item['id'])
            context.adapter.push_commands([cmd])


class MoveToInbox(Intent):
    help_text = 'Move selected item to inbox'

    @staticmethod
    def execute(context, arg):
        if context.vars['active_tag'] and context.model['items']:
            item = context.model['items'][context.vars['active_item']]
            cmd = commands.UnsetTagCommand(item['id'])
            context.adapter.push_commands([cmd])


class DeleteTag(Intent):
    help_text = 'Delete selected tag'

    @staticmethod
    def execute(context, arg):
        if not context.model['tags'][context.vars['active_tag']]['count']:
            cmd = commands.DeleteTagCommand(
                context.model['tags'][context.vars['active_tag']]['name'])
            context.adapter.push_commands([cmd])


keymap = {
    'l': PreviousTag,
    'K': PreviousTag,
    'h': NextTag,
    'J': NextTag,
    'k': PreviousItem,
    'j': NextItem,
    'a': AddItem,
    KEY_ENTER: AddItem,
    'p': Process,
    'd': DeleteItem,
    'x': DeleteItem,
    'i': MoveToInbox,
    'D': DeleteTag,
}
