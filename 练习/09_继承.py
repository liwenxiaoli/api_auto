class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        print(f"{self.name} 发出了声音")


class Dog(Animal):
    def speak(self):                                                        #重写了用自己的
        print(f"{self.name} 汪汪叫")

    def fetch(self):
        print(f"{self.name} 跑去捡球")

class Puppy(Animal):
    def __init__(self, name, age):
        super().__init__(name)      # ← 让父类帮忙存 name     #用父类的speak
        self.age = age


p = Puppy("小白", 3)
p.speak()

print("年龄:", p.age)
d = Dog("旺财")
d.speak()
d.fetch()
print("名字:", d.name)
#继承 Anima