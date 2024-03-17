from random import shuffle
from discord import Message, Thread, Embed
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
from config.trapper_constants import trapper_constants
import views.panels.panel_training as panel_training


class Pick_Trap_Panel_First:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_pick_trap_panel_first(self) -> None:

      
        trainer = panel_training.TrainPanel(self.pid, self.sid,
                                            self.iid, self.status_message, self.status_panel_generator, self.thread)
        await trainer.get_train_panel()
