import sys
import inspect

from src.fsm_forms.add_drug_form import *
from src.fsm_forms.report_druguse_form import *
from src.fsm_forms.report_paincase_form import *
from src.fsm_forms.donate_form import *
from src.fsm_forms.pressure_form import *
from src.fsm_forms._custom import CustomState


# Get all instances of StatesGroup from this module
available_fsm_states = []
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and issubclass(obj, StatesGroup):
        obj: StatesGroup
        # Get all state names from the StatesGroup
        state_names = obj.states_names
        for i, state_name in enumerate(state_names):
            state_name_list = state_name.split(':')  # ReportPainCaseForm:durability
            available_fsm_states.append(f'{state_name_list[0]}:{i}:{state_name_list[1]}')
