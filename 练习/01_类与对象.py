

class RemoteControl:
    def __init__(self, brand):
        self.brand = brand

    def press(self, button):
        print(f"{self.brand} 遥控器按下了「{button}」")




rc1 = RemoteControl("小米")
rc1.press("换台")
rc2 = RemoteControl("索尼")
rc2.press("音量+")
