import views.panels.panel_buying as panel_buying
import views.panels.panel_tips as panel_tips
import views.panels.panel_training as panel_training
import views.panels.panel_pick_skill as panel_pick_skill

class panel_interpreter:
    def __init__(self, panel) -> None:
        self.panel=panel
    async def get(self) -> None:
        if isinstance(self.panel,panel_training.TrainPanel):
            await self.panel.get_train_panel()
            return
        if isinstance(self.panel,panel_tips.TipPanel):
            await self.panel.get_tip_panel()
            return
        if isinstance(self.panel,panel_buying.BuyPanel):
            await self.panel.get_buy_panel()
            return
        if isinstance(self.panel,panel_pick_skill.PickSkillPanel):
            await self.panel.get_pick_skill_panel()
            return
        
        print("OOPS!, INTERFACE CALLED ON IMPOSSIBLE SHOP")

