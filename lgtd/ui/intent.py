from ..lib import commands

IM_ADD = 0
IM_EDIT = 1
IM_PROC = 2


class Intent(object):
    help_text = None

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        raise NotImplemented


class PreviousTag(Intent):
    help_text = 'Move to previous tag'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        active = max(0, ui_state['active_tag'] - 1)
        if ui_state['active_tag'] != active:
            ui_state['active_item'] = 0
            ui_state['active_tag'] = active
            state_adapter.request_state(
                model_state['tags'][active]['name'])


class NextTag(Intent):
    help_text = 'Move to next tag'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        active = min(len(model_state['tags']) - 1, ui_state['active_tag'] + 1)
        if ui_state['active_tag'] != active:
            ui_state['active_item'] = 0
            ui_state['active_tag'] = active
            state_adapter.request_state(
                model_state['tags'][active]['name'])


class PreviousItem(Intent):
    help_text = 'Move to previous item'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        ui_state['active_item'] = max(0, ui_state['active_item']-1)


class NextItem(Intent):
    help_text = 'Move to next item'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        ui_state['active_item'] = min(
            len(model_state['items']) - 1,
            ui_state['active_item'] + 1)


class AddItem(Intent):
    help_text = 'Add new item'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        ui_state['input_mode'] = IM_ADD
        ui_state['input_buffer'] = ''


class Process(Intent):
    help_text = 'Process selected item'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        if ui_state['active_tag'] == 0 and model_state['tags'][0]['count']:
            ui_state['input_mode'] = IM_PROC
            ui_state['input_buffer'] = ''


class DeleteItem(Intent):
    help_text = 'Delete selected item'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        if model_state['items']:
            item = model_state['items'][ui_state['active_item']]
            cmd = commands.DeleteItemCommand(item['id'])
            state_adapter.push_commands([cmd])


class MoveToInbox(Intent):
    help_text = 'Move selected item to inbox'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        if ui_state['active_tag'] and model_state['items']:
            item = model_state['items'][ui_state['active_item']]
            cmd = commands.UnsetTagCommand(item['id'])
            state_adapter.push_commands([cmd])


class DeleteTag(Intent):
    help_text = 'Delete selected tag'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        if not model_state['tags'][ui_state['active_tag']]['count']:
            cmd = commands.DeleteTagCommand(
                model_state['tags'][ui_state['active_tag']]['name'])
            state_adapter.push_commands([cmd])


class SelectTag(Intent):
    help_text = 'Select tag #'

    @staticmethod
    def execute(char, ui_state, model_state, state_adapter):
        n = (char - ord('0') + 9) % 10
        if n < len(model_state['tags']) and n != ui_state['active_tag']:
            ui_state['active_tag'] = n
            ui_state['active_item'] = 0
            state_adapter.request_state(model_state['tags'][n]['name'])
