import discord
from discord.ext import commands, bridge, tasks
import random
from random import choices
from collections import defaultdict
from dotenv import load_dotenv
import json
import os

load_dotenv()

bot_key = os.getenv("BOT_KEY")

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Bot()
bot = bridge.Bot(command_prefix='!', intents=intents)

players = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Update..."))
    print("Launch success!")

class Equipment:
    def __init__(self, name, atk=0, defi=0, mag=0, mdf=0, spd=0, lck=0, heal_percent=0, heal_fixed=0, cost=0, tags=None):
        if tags is None:
            tags = []
        self.name = name
        self.atk = atk
        self.defi = defi
        self.mag = mag
        self.mdf = mdf
        self.spd = spd
        self.lck = lck
        self.heal_percent = heal_percent
        self.heal_fixed = heal_fixed
        self.cost = cost
        self.tags = tags

class Inventory:
    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    def add_items(self, items):
        self.items.extend(items)

    def is_in_inventory(self, name):
        for item in self.items:
            if item.name == name:
                return True
        return False
    
    def remove_from_inventory(self, item):
        if item in self.items:
            self.items.remove(item)
            return True
        return False
    
    def get_items_by_tag(self, tag):
        return [item for item in self.items if tag in item.tags]

heal_posion = Equipment(name="Зелье исцеления", heal_percent=30, tags=["item", "heal"])
scareed_helmet = Equipment(name="Потрёпанный шлем", tags=["head", "armo"])
army_armour = Equipment(name="Армейская броня", tags= ["body", "armo"])
shield = Equipment(name="Щит", tags=["larm", "armo"])
army_sword = Equipment(name="Армейский меч", atk=10, spd=5, tags=["rarm", "armo"])
new_sword = Equipment(name="Новый меч", tags=["rarm", "armo"])
ring = Equipment(name="Кольцо", tags=["ring", "armo"])

wolf_fang = Equipment(name="Волчий клык", cost=100, tags=["item"])
wolf_skin = Equipment(name="Волчья шкура", cost=300, tags=["item"])
white_wolf_skin = Equipment(name="Белая шкура", cost=600, tags=["item"])
man_meat = Equipment(name="Мясо оборотня", heal_fixed=300, tags=["item", "heal"])

inventory = Inventory()
inventory.add_items([heal_posion, heal_posion, scareed_helmet, army_armour, shield, army_sword, ring])

class Player:

    def __init__(self, user):
        self.id = user.id
        self.user = user
        self.maxhp = 100
        self.health = 100
        self.money = 100
        self.next = 1000
        self.lvl = 1
        self.kills = 0

        self.atk = 10
        self.defi = 10 
        self.mag = 10
        self.mdf = 10
        self.spd = 10 
        self.lck = 10 

        self.head = None
        self.rarm = None
        self.larm = None
        self.body = None

        self.ring1 = None
        self.ring2 = None
        self.ring3 = None
        self.ring4 = None

        self.curret_monster = None

        self.inFight = False
        self.turn = False
        self.addturn = True

        self.wins = 0
        self.loses = 0
        self.current_quest = None

    def attack(self, monster):
        damage = self.atk*4-monster.defi*2
        monster.health -= round(damage, 0)
        return damage

    def flee(self):
        self.curret_monster = None
        self.inFight = False
    
    def equip(self, slot, item):
        if getattr(self, slot):
            self.unequip(slot)
        setattr(self, slot, item)
        self.atk += item.atk
        self.defi += item.defi
        self.mag += item.mag
        self.mdf += item.mdf
        self.spd += item.spd
        self.lck += item.lck

    def unequip(self, slot):
        item = getattr(self, slot)
        if item:
            self.atk -= item.atk
            self.defi -= item.defi
            self.mag -= item.mag
            self.mdf -= item.mdf
            self.spd -= item.spd
            self.lck -= item.lck
            setattr(self, slot, None)

    def to_dict(self):
        return {
            "maxhp": self.maxhp,
            "health": self.health,
            "money": self.money,
            "next": self.next,
            "lvl": self.lvl,
            "kills": self.kills,
            "inv": self.inventory,
            "wins": self.wins,
            "loses": self.loses,
        }

    def save(self):

        pid = str(self.id)

        player_data = self.to_dict()

        try:
            with open('player_data.json', 'r') as file:
                existing_data = json.load(file)
                
            if pid in existing_data:  
                existing_data[pid] = player_data  
            else:
                existing_data.update({pid: player_data}) 
                    
        except FileNotFoundError:
            existing_data = {pid: player_data}

        with open('player_data.json', 'w') as file:
            json.dump(existing_data, file, indent=4)

    def get_monster_lvl(self):
        level_range_start = max(1, self.lvl - 2)
        level_range_end = self.lvl + 2
        
        monster_lvl = random.randint(level_range_start, level_range_end)
        return monster_lvl

class PlayerUI(discord.ui.View):
    @discord.ui.button(row = 0,label="Снаряжение", style=discord.ButtonStyle.primary)
    async def equipment(self, button, interaction):
        await interaction.response.edit_message(content="", view = PlayerEquipment())

    @discord.ui.button(row = 1,label="Инвентарь", style=discord.ButtonStyle.primary)
    async def inventory(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("item")
        await interaction.response.edit_message(content="", view = ItemView(player, items, inv=True))

    @discord.ui.button(row = 2,label="Статистика", style=discord.ButtonStyle.primary)
    async def statisticks(self, button, interaction):
        player = players.get(interaction.user.id)
            
        retStr = (
            f"""**Имя:** {player.user.name}
            **Здоровье:** {player.health} / {player.maxhp} hp
            **Уровень:** {player.lvl}
            **Урон:** {player.attack}
            **Монеты:** Œ{player.money}
            **Опыт:** {player.exp} / {player.next} op
            **Убийства:** {player.kills}
            
           **Характеристики:**
            **ATK:** {player.atk}
            **DEF:** {player.defi} 
            **MAG:** {player.mag}
            **MDF:** {player.mdf}
            **SPD:** {player.spd}
            **LCK:** {player.lck}
            """
        )

        if player.current_quest:
            retStr += (
                f"""\n**Ежедневное задание:**
                Цель: {player.current_quest.monster_class.name}
                Осталось убить: {player.current_quest.quantity - player.current_quest.progress} / {player.current_quest.quantity}
                Награда: Œ{player.current_quest.get_reward()}"""
            )
        else:
            retStr += "\n\n**Ежедневное задание:**\n- Задание завершено"
        
        embed = discord.Embed(title="**Статистика**",colour=discord.Colour.gold())
        embed.add_field(name="",value=retStr)
        await interaction.response.edit_message(content="",embed = embed,view=Back())

    @discord.ui.button(row = 3,label="Назад", style=discord.ButtonStyle.primary)
    async def back(self, button, interaction):
        await interaction.response.edit_message(content="", view = City())


class Back(discord.ui.View): # пиздец
    @discord.ui.button(row = 0,label="Назад", style=discord.ButtonStyle.primary) 
    async def fuckoff(self, button, interaction):
        await interaction.response.edit_message(content="", embed = None, view = PlayerUI())

class PlayerEquipment(discord.ui.View):
    @discord.ui.button(row = 0,label="Голова", style=discord.ButtonStyle.primary)
    async def ehead(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("head")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 0,label="Тело", style=discord.ButtonStyle.primary)
    async def ebody(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("body")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 1,label="Левая рука", style=discord.ButtonStyle.primary)
    async def elram(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("larm")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 1,label="Правая рука", style=discord.ButtonStyle.primary)
    async def erarm(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("rarm")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 2,label="Кольцо 1", style=discord.ButtonStyle.primary)
    async def ring1(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("ring")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 2,label="Кольцо 2", style=discord.ButtonStyle.primary)
    async def ring2(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("ring")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 2,label="Кольцо 3", style=discord.ButtonStyle.primary)
    async def ring3(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("ring")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 2,label="Кольцо 4", style=discord.ButtonStyle.primary)
    async def ring4(self, button, interaction):
        player = players.get(interaction.user.id)
        items = inventory.get_items_by_tag("ring")
        await interaction.response.edit_message(content="", view = ItemView(player, items))

    @discord.ui.button(row = 3,label="Назад", style=discord.ButtonStyle.primary)
    async def goback(self, button, interaction):
        await interaction.response.edit_message(content="", view = PlayerUI())

class ItemView(discord.ui.View):
    def __init__(self, player, items, page=0, interaction_type="use", inv=False):
        super().__init__()
        self.player = player
        self.items = items
        self.page = page
        self.interaction_type = interaction_type
        self.inv = inv
        self.add_buttons()

    def add_buttons(self):
        start = self.page * 20
        end = start + 20
        paginated_items = self.items[start:end]

        for item in paginated_items:
            label = item.name
            if self.interaction_type == "buy" or self.interaction_type == "sell":
                label += f" Œ{item.cost}"
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary)
            button.callback = self.create_callback(item)
            self.add_item(button)

        prev_button = discord.ui.Button(
            emoji="⏪", 
            row=4, 
            style=discord.ButtonStyle.secondary, 
            disabled=self.page <= 0
        )
        if self.page > 0:
            prev_button.callback = self.create_prev_page_callback()
        self.add_item(prev_button)

        goback_button = discord.ui.Button(label="Назад", row=4, style=discord.ButtonStyle.primary)
        goback_button.callback = self.goback()
        self.add_item(goback_button)

        next_button = discord.ui.Button(
            emoji="⏩", 
            row=4, 
            style=discord.ButtonStyle.secondary, 
            disabled=end >= len(self.items)
        )
        if end < len(self.items):
            next_button.callback = self.create_next_page_callback()
        self.add_item(next_button)


    def create_callback(self, item):
        async def callback(interaction):
            if self.interaction_type == "use":
                await interaction.response.edit_message(content=f"Вы хотите использовать {item.name}?", view=ChoiceUniversal(item))
            elif self.interaction_type == "buy":
                await interaction.response.edit_message(content=f"Вы хотите купить {item.name} за Œ{item.cost}?", view=ChoiceBuy(item, self.items))
            elif self.interaction_type == "sell":
                await interaction.response.edit_message(content=f"Вы хотите продать {item.name} за Œ{item.cost}?", view=ChoiceSell(item, self.items))
        return callback
    
    def create_next_page_callback(self):
        async def callback(interaction):
            next_page = ItemView(self.player, self.items, self.page + 1, self.interaction_type)
            await interaction.response.edit_message(content="", view=next_page)
        return callback

    def create_prev_page_callback(self):
        async def callback(interaction):
            prev_page = ItemView(self.player, self.items, self.page - 1, self.interaction_type)
            await interaction.response.edit_message(content="", view=prev_page)
        return callback

    def goback(self):
        async def callback(interaction):
            if self.interaction_type == "use":
                if self.inv:
                    await interaction.response.edit_message(content="", view=PlayerUI())
                await interaction.response.edit_message(content="", view=PlayerEquipment())
            elif self.interaction_type == "buy" or self.interaction_type == "sell":
                await interaction.response.edit_message(content="", view=Traders(), embed=None)
        return callback

class ChoiceUniversal(discord.ui.View):
    def __init__(self, item):
        super().__init__()
        self.item = item
    
    @discord.ui.button(row=0, label="Да", style=discord.ButtonStyle.primary)
    async def ja(self, button, interaction):
        tag_handlers = {
            "heal": self.handle_heal,
            "armo": self.handle_armo,
        }
        for tag in self.item.tags:
            if tag in tag_handlers:
                await tag_handlers[tag](interaction, self.item)
                break

    async def handle_heal(self, interaction, item):
        player = players.get(interaction.user.id)
        healed = ""
        if hasattr(item, 'heal_fixed'):
            healed = item.heal_fixed
            player.health += healed
        if hasattr(item, 'heal_percent'):
            healed = player.maxhp * (item.heal_percent / 100)
            player.health += healed
        if player.health > player.maxhp:
            player.health = player.maxhp
        inventory.remove_from_inventory(item)
        await interaction.response.edit_message(content=f"Вы использовали {item.name} и исцелились на {healed}", view=ItemView(player, inventory.get_items_by_tag("item")))

    async def handle_armo(self, interaction, item):
        player = players.get(interaction.user.id)
        if getattr(player, item.tags[0]) != item:
            player.equip(item.tags[0], item)
        await interaction.response.edit_message(content=f"Вы теперь используете {item.name}.", view=ItemView(player, inventory.get_items_by_tag(f"{item.tags[0]}")))

    @discord.ui.button(row=0, label="Нет", style=discord.ButtonStyle.primary)
    async def nein(self, button, interaction):
        player = players.get(interaction.user.id)
        await interaction.response.edit_message(content="", view=ItemView(player, inventory.get_items_by_tag("item")))

class ChoiceBuy(discord.ui.View):
    def __init__(self, item, items_for_sale):
        super().__init__()
        self.item = item
        self.items_for_sale = items_for_sale
    
    @discord.ui.button(row=0, label="Да", style=discord.ButtonStyle.primary)
    async def ja(self, button, interaction):
        player = players.get(interaction.user.id)
        if player.money >= self.item.cost:
            player.money -= self.item.cost
            inventory.add_item(self.item)
            await interaction.response.edit_message(content=f"{self.item.name} добавлен в инвентарь.", view=ItemView(player, self.items_for_sale, interaction_type="buy"))
        else:
            await interaction.response.edit_message(content=f"Недостаточно средств.", view=ItemView(player, self.items_for_sale, interaction_type="buy"))

    @discord.ui.button(row=0, label="Нет", style=discord.ButtonStyle.primary)
    async def nein(self, button, interaction):
        player = players.get(interaction.user.id)
        await interaction.response.edit_message(content="", view=ItemView(player, self.items_for_sale, interaction_type="buy"))

class ChoiceSell(discord.ui.View):
    def __init__(self, item, items_for_sale):
        super().__init__()
        self.item = item
        self.items_for_sale = items_for_sale
    
    @discord.ui.button(row=0, label="Да", style=discord.ButtonStyle.primary)
    async def ja(self, button, interaction):
        player = players.get(interaction.user.id)
        player.money += self.item.cost
        name = self.item.name
        inventory.remove_from_inventory(self.item)
        await interaction.response.edit_message(content=f"{name} продан.", view=ItemView(player, self.items_for_sale, interaction_type="sell"))

    @discord.ui.button(row=0, label="Нет", style=discord.ButtonStyle.primary)
    async def nein(self, button, interaction):
        player = players.get(interaction.user.id)
        await interaction.response.edit_message(content="", view=ItemView(player, self.items_for_sale, interaction_type="sell"))

# ================================================================ Квест(ы) ================================================================

class DailyQuest:
    def __init__(self, monster_class, quantity):
        self.monster_class = monster_class
        self.quantity = quantity
        self.progress = 0
        self.reward = self.calculate_reward()

    def calculate_reward(self):
        reward_dict = {'Волк': 100, 'Белый Волк': 150, 'Вервольф': 300, 'Вервольф в броне': 400, 'Вервольф-Вожак': 1000, 'Зверь из Мосскрита': 2000,}
        rew = reward_dict[self.monster_class.name] * self.quantity
        return rew

    def update_progress(self, monster):
        if monster.name == self.monster_class.name:
            self.progress += 1

    def is_completed(self):
        return self.progress >= self.quantity                  

    def get_reward(self):
        return self.reward

# ================================================================ О МОНСТР КУРВА ================================================================

class Monster:
    def __init__(self, id, name, level, health, drops, img, attack = 10, defence = 10, magick = 10, magdefence = 10, speed = 10):
        self.id = id
        self.name = name
        self.level = level
        self.health = round(health * 1.1 ** level, 0)
        self.drops = drops
        self.img = img

        self.atk = attack
        self.defi = defence 
        self.mag = magick
        self.mdf = magdefence
        self.spd = speed 

        self.spells = [self.spell1, self.spell2, self.spell3, self.spell4]

    def attack_player(self, player):
        damage = self.atk*4 - player.defi*2
        player.health -= round(damage, 0)
        return damage

    def drop_items(self):
        dropped_items = []
        for item, drop_chance in self.drops.items():
            if random.random() < drop_chance:
                dropped_items.append(item)
        return dropped_items
    
    def spell1(self, player=None):
        raise NotImplementedError("Pivo1")

    def spell2(self, player=None):
        raise NotImplementedError("Pivo2")

    def spell3(self, player=None):
        raise NotImplementedError("Pivo3")

    def spell4(self, player=None):
        raise NotImplementedError("Pivo4")

class Wolf(Monster):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spells = [self.spell1]

    def spell1(self, player):
        self.atk += 5

class WhiteWolf(Monster):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spells = [self.spell1]

    def spell1(self, player):
        self.health += 50

class Werewolf(Monster):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spells = [self.spell1]

    def spell1(self, player):
        damage = self.atk * 4 - player.defi * 1.8
        player.health -= round(damage, 0)
        return damage

class ArmoredWerewolf(Monster):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spells = [self.spell1, self.spell2]

    def spell1(self, player):
        self.defi += 10

    def spell2(self, player):
        damage = self.atk * 4 - player.defi * 1.8
        player.health -= round(damage, 0)

class Boss:
    def __init__(self, id, name, health, spellname, spell2name, drops, img, attack = 10, defence = 10, magick = 10, magdefence = 10, speed = 10):
        self.id = id
        self.name = name
        self.health = health
        self.spellname = spellname
        self.spell2name = spell2name
        self.drops = drops
        self.img = img

        self.atk = attack
        self.defi = defence 
        self.mag = magick
        self.mdf = magdefence
        self.spd = speed 

    def attack_player(self, player):
        damage = self.atk*4 - player.defi*2
        player.health -= round(damage, 0)
        return damage

    def drop_items(self):
        dropped_items = []
        for item, drop_chance in self.drops.items():
            if random.random() < drop_chance:
                dropped_items.append(item)
        return dropped_items

class Leader(Boss):
    def spell1(self, player):
        atk = player.attack
        procent = 15
        freezing = atk - (atk * procent / 100)
        return freezing
    
    def spell2(self, player):
        damage = 120  
        player.health -= round(damage, 0)

class Beast(Boss):
    def spell1(self, player):
        damage = 290  
        player.health -= round(damage, 0)
    
    def spell2(self):
       self.attack = self.attack * 1.5

# ================================================================ АРЕНА БЛЭТ ================================================================

class Arena(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.player1 = None
        self.player2 = None
    
    @discord.ui.button(row = 0,label="Игрок 1, участие Œ500", style=discord.ButtonStyle.primary)
    async def pl1(self, button, interaction):
        if self.player2 is not None and interaction.user.id == self.player2.id:
            await interaction.response.edit_message(content="Нельзя играть с самим собой")
        else:
            self.player1 = players.get(interaction.user.id)
            await interaction.response.edit_message(content=f"Приветствуем первого игрока {self.player1.user.name}")

    @discord.ui.button(row = 0,label="Игрок 2, участие Œ500", style=discord.ButtonStyle.primary) 
    async def pl2(self, button, interaction):
        if self.player1 is not None and interaction.user.id == self.player1.id:
            await interaction.response.edit_message(content="Нельзя играть с самим собой")
        else:
            self.player2 = players.get(interaction.user.id)
            await interaction.response.edit_message(content=f"Приветствуем второго игрока {self.player2.user.name}")

    @discord.ui.button(row = 1,label="Начать", style=discord.ButtonStyle.primary) 
    async def start(self, button, interaction):
        if self.player1 is None or self.player2 is None:
            await interaction.response.edit_message(content="Недостаточно игроков")
        elif self.player1.money or self.player2.money < 500:
            await interaction.response.edit_message(content="У одного из игроков недостаточно средств")
        else:
            self.player1.money -= 500
            self.player2.money -= 500
            await interaction.response.edit_message(content="Началась дуэль между {self.player1.user.name} и {self.player2.user.name}", view=FightArena(player1=self.player1, player2 = self.player2))

    @discord.ui.button(row = 2,label="Назад", style=discord.ButtonStyle.primary) 
    async def exita(self, button, interaction):
        self.player1 = None
        self.player2 = None
        await interaction.response.edit_message(content="Вы вышли в город", view = City())


class FightArena(discord.ui.View):
    def __init__(self, player1, player2):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.player1.turn = True


    @discord.ui.button(row = 0,label="Атаковать", style=discord.ButtonStyle.primary)
    async def atk(self, button, interaction):

        message = ""

        
        
        if interaction.user.id == self.player1.id and self.player1.turn:
            
            damage = self.player1.hit()
            self.player2.health -= damage
            self.player2.save()
            
            message = f"{self.player1.user.name} наносит {self.player2.user.name} {damage} урона\nУ {self.player2.user.name} {self.player2.health}hp"
            
            if self.player2.health <= 0:
                self.player1.kills += 1
                self.player1.wins += 1
                self.player2.money += 1000
                self.player2.exp += 250
                self.player2.loses += 1
                self.player1.save()
                self.player2.save()
                
                await interaction.response.edit_message(f"{self.player1.user.name} повержен", view = City())
                self.player1 = None
                self.player2 = None
            else:
                self.player1.turn = False
                self.player2.turn = True
                message += f"\nСейчас ход игрока {self.player2.user.name}"
                
        elif interaction.user.id == self.player2.id and self.player2.turn:
            
            damage = self.player2.hit()
            self.player1.health -= damage
            self.player1.save()
            
            message = f"{self.player2.user.name} наносит {self.player1.user.name} {damage} урона\nУ {self.player1.user.name} {self.player1.health} hp"
            
            if self.player1.health <= 0:
                self.player2.kills += 1
                self.player2.wins += 1
                self.player2.money += 1000
                self.player2.exp += 250
                self.player1.loses += 1
                self.player1.save()
                self.player2.save()
                
                await interaction.response.edit_message(f"{self.player1.user.name} повержен", view = City())
                self.player1 = None
                self.player2 = None
            else:
                self.player2.turn = False
                self.player1.turn = True
                message += f"\nСейчас ход игрока {self.player1.user.name}"
        else:
            message = "Сейчас не ваш ход"

        await interaction.response.edit_message(content=message)


    @discord.ui.button(row = 0,label="Подлечиться", style=discord.ButtonStyle.primary)
    async def hel(self, button, interaction):
        
        message = ""
        
        player = None
        
        if interaction.user.id == self.player1.id:
            if self.player1.turn:
                player = self.player1
            else:
                message = "Сейчас не ваш ход"
        elif interaction.user.id == self.player2.id:
            if self.player2.turn:
                player = self.player2
            else:
                message = "Сейчас не ваш ход"

        if player:
            if player.check_item('Зелье исцеления'):        
                amount = player.heal()
                player.health += amount

                player.save()

                message = f"{player.user.name} исцелился на {amount}hp"

                if player.health > player.maxhp:
                    damage = random.randint(10, player.heal_amount)
                    player.health -= damage
                    player.save()

                    message = (
                        f"Вы выпили слишком много зелья исцеления, у вас интоксикация! "
                        f"Вы получили {damage} урона!"
                    )

                    player.remove_item('Зелье исцеления')
                else:
                    message = "У вас не осталось зелий исцеления"

                if player == self.player1:
                    self.player1.turn = False
                    self.player2.turn = True
                else:
                    self.player1.turn = True
                    self.player2.turn = False
        
        await interaction.response.edit_message(content=message)
                            
        
    @discord.ui.button(row = 0,disabled = True ,label="Герои не бегут", style=discord.ButtonStyle.primary)
    async def run(self, button, interaction):
        await interaction.response.edit_message("Внатуре")

# ================================================================ ТОРГАШИ ================================================================

class Traders(discord.ui.View):
    @discord.ui.button(row = 0,label="Людвиг, Святой меч", style=discord.ButtonStyle.primary)
    async def gotoludwig(self, button, interaction):
         embed = discord.Embed (description = "Вновь приветствую.", colour=0x8f0000)
         embed.set_image(url = "")
         await interaction.response.edit_message(content="Вы зашли в небольшую кузницу, рядом с магазином", embed = embed, view = Ludvig())

    @discord.ui.button(row = 1, label="Жанна, Торговка", style=discord.ButtonStyle.primary)
    async def gotojanne(self, button, interaction):
         embed = discord.Embed (description = "Здравствуйте!", colour=0x8f0000)
         embed.set_image(url = "")
         await interaction.response.edit_message(content="Вы зашли в магазин, где-то в центре города.", embed = embed, view = Jeanne())

    @discord.ui.button(row = 2, label="Виктория, Жрица", style=discord.ButtonStyle.primary)
    async def gotovictoria(self, button, interaction):
         embed = discord.Embed (description = "Чем могу помочь?", colour=0x8f0000)
         embed.set_image(url = "")
         await interaction.response.edit_message(content="Вы в каменную церковь, на самом краю города.", embed = embed, view = Victoria())

    @discord.ui.button(row = 3,label="Назад", style=discord.ButtonStyle.primary) 
    async def tocit(self, button, interaction):
        await interaction.response.edit_message(content="", view = City())

# ================================================================ ЛЮДВИГ ================================================================

class Ludvig(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.items = [new_sword]

    @discord.ui.button(row = 0,label="Товары", style=discord.ButtonStyle.primary) 
    async def towars(self, button, interaction):
        player = players.get(interaction.user.id)
        await interaction.response.edit_message(content="",view=ItemView(player, self.items, interaction_type="buy"))

    @discord.ui.button(row = 1,label="Улучшить оружие", style=discord.ButtonStyle.primary) 
    async def upgrade(self, button, interaction):
        pass

    @discord.ui.button(row = 2,label="Задания", style=discord.ButtonStyle.primary) 
    async def quests(self, button, interaction):
        pass

    @discord.ui.button(row = 3,label="Убить", style=discord.ButtonStyle.primary) 
    async def kill(self, button, interaction):
        pass

    @discord.ui.button(row = 4,label="Назад", style=discord.ButtonStyle.primary) 
    async def tocit(self, button, interaction):
        await interaction.response.edit_message(content="", embed = None, view = Traders())

# ================================================================ ВИКТОРИЯ ================================================================

class Victoria(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.items = [heal_posion]

    @discord.ui.button(row = 0,label="Товары", style=discord.ButtonStyle.primary) 
    async def towars(self, button, interaction):
        player = players.get(interaction.user.id)
        await interaction.response.edit_message(content="",view=ItemView(player, self.items, interaction_type="buy"))

    @discord.ui.button(row = 1,label="Исцелиться", style=discord.ButtonStyle.primary) 
    async def heal(self, button, interaction):
        player = players.get(interaction.user.id)

        if player.health == player.maxhp:
            await interaction.response.edit_message(content=f"Вы и так здоровы")
        else:
            player.health = player.maxhp
            player.save()
            await interaction.response.edit_message(content=f"Вы исцелились на максимум hp. У вас теперь {player.health} hp",)

    @discord.ui.button(row = 2,label="Поговорить", style=discord.ButtonStyle.primary) 
    async def quests(self, button, interaction):
        pass
    @discord.ui.button(row = 3,label="Убить", style=discord.ButtonStyle.primary) 
    async def kill(self, button, interaction):
        pass

    @discord.ui.button(row = 4, label="Назад", style=discord.ButtonStyle.primary) 
    async def back(self, button, interaction):
        await interaction.response.edit_message(content="", embed = None, view = Traders())

# ================================================================ ЖАННА ================================================================

class Jeanne(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.items = [ring]

    @discord.ui.button(row = 0,label="Товары", style=discord.ButtonStyle.primary) 
    async def towars(self, button, interaction):
        player = players.get(interaction.user.id)
        await interaction.response.edit_message(content="",view=ItemView(player, self.items, interaction_type="buy"))

    @discord.ui.button(row = 1,label="Продать дроп", style=discord.ButtonStyle.primary) 
    async def sell_all(self, button, interaction):
        player = players.get(interaction.user.id)
        await interaction.response.edit_message(content=f"", view = ItemView(player, inventory.items, interaction_type="sell"))

    @discord.ui.button(row = 2,label="Поговорить", style=discord.ButtonStyle.primary) 
    async def quests(self, button, interaction):
        pass

    @discord.ui.button(row = 3,label="Убить", style=discord.ButtonStyle.primary) 
    async def kill(self, button, interaction):
        pass

    @discord.ui.button(row = 4,label="Назад", style=discord.ButtonStyle.primary) 
    async def tocit(self, button, interaction):
        await interaction.response.edit_message(content="", embed = None, view = Traders())
        
# ================================================================ ГОРОД БЕЗ МАТА ================================================================


class City(discord.ui.View):
    @discord.ui.button(row = 0,label="В бой!", style=discord.ButtonStyle.primary) 
    async def gotofight(self, button, interaction):
        await interaction.response.edit_message(content="Куда отправиться?", view = Locations())

    @discord.ui.button(row = 1, label="Торговцы", style=discord.ButtonStyle.primary)
    async def toshop(self, button, interaction):
        await interaction.response.edit_message(content="",view = Traders())

    @discord.ui.button(row = 2, label="На арену", style=discord.ButtonStyle.primary, disabled=True)
    async def arena(self, button, interaction):
        await interaction.response.edit_message(content="Добро пожаловать на убой", view = Arena())

    @discord.ui.button(row = 3,label="Персонаж", style=discord.ButtonStyle.primary)
    async def playerui(self, button, interaction):
        await interaction.response.edit_message(content="", view = PlayerUI())


# ================================================================ ЛОКАЦИИ ЁПТА ================================================================

class Locations(discord.ui.View):

    @discord.ui.button(row = 0, label="Волчий лес", style=discord.ButtonStyle.primary) 
    async def wolfsforest(self, button, interaction):
            player = players.get(interaction.user.id)

            mlvl = player.get_monster_lvl()
            
            wolf = Wolf(1001, "Волк", mlvl, 100, {wolf_fang: 0.5, wolf_skin: 0.3}, 'https://i.imgur.com/cjOvipe.png')
            wwolf = WhiteWolf(1002, "Белый Волк", mlvl, 200, {wolf_fang: 0.7, white_wolf_skin: 0.5}, 'https://i.imgur.com/kcPiYNr.png')
            werewolf = Werewolf(1010, "Вервольф", mlvl, 150, {wolf_skin: 0.5, man_meat: 0.2}, 'https://i.imgur.com/6pu8XQs.png')

            creatures = [wolf, wwolf, werewolf]
            weights = [50, 25, 15]

            player.curret_monster = random.choices(creatures, weights)[0]

            embed = discord.Embed(title=f"За деревьями виднеется {player.curret_monster.name}", colour=0x8f0000)
            embed.set_image(url=player.curret_monster.img)

            await interaction.response.edit_message(content="",embed=embed,view = Fight())


    @discord.ui.button(row = 2, label="Сожжёная деревня", style=discord.ButtonStyle.primary)
    async def burnedvillage(self, button, interaction):
            player = players.get(interaction.user.id)

            mlvl = player.get_monster_lvl()

            werewolf = Werewolf(1010, "Вервольф",  mlvl, 150, {"Волчья шкура": 0.5, "Человечина": 0.2}, 'https://i.imgur.com/6pu8XQs.png')
            awerewolf = ArmoredWerewolf(1020, "Вервольф в броне", mlvl, 250, {"Волчья шкура": 0.7, "Человечина": 0.3}, 'https://i.imgur.com/wUpilNG.png')
            leader = Leader(1100, "Вервольф-Вожак", 750, "Жуткий вой", "Стальные когти", {"Волчья шкура": 0.6, "Человечина": 0.4, "Амулет": 0.05}, 'https://i.imgur.com/xJ3zOkK.png')

            creatures = [werewolf, awerewolf, leader]
            weights = [35, 50, 10]

            player.curret_monster = random.choices(creatures, weights)[0]

            embed = discord.Embed(title=f"На вас вышел {player.curret_monster.name}", colour=0x8f0000)
            embed.set_image(url=player.curret_monster.img)

            await interaction.response.edit_message(content="",embed=embed,view = Fight())

    @discord.ui.button(row = 1, label="Тёмная пещера", style=discord.ButtonStyle.primary)
    async def darkcave(self, button, interaction):
            player = players.get(interaction.user.id)

            mlvl = player.get_monster_lvl()

            werewolf = Werewolf(1010, "Вервольф",  mlvl, 150, {"Волчья шкура": 0.5, "Человечина": 0.2}, 'https://i.imgur.com/6pu8XQs.png')
            awerewolf = ArmoredWerewolf(1020, "Вервольф в броне", mlvl, 250, {"Волчья шкура": 0.7, "Человечина": 0.3}, 'https://i.imgur.com/wUpilNG.png')
            beast = Beast(1200, "Зверь из Мосскрита", 1550, "В клочья", "Всплеск адреналина", {"Волчья шкура": 0.6, "Сердце волка": 0.1}, 'https://i.imgur.com/v6wtISO.png')

            creatures = [werewolf ,awerewolf, beast]
            weights = [50, 40, 15]

            player.curret_monster = random.choices(creatures, weights)[0]

            embed = discord.Embed(title=f"Из темноты вышел {player.curret_monster.name}", colour=0x8f0000)
            embed.set_image(url=player.curret_monster.img)

            await interaction.response.edit_message(content="",embed=embed,view = Fight())

    @discord.ui.button(row = 3, label="Улицы столицы", style=discord.ButtonStyle.primary)
    async def capitalstreets(self, button, interaction):
            player = players.get(interaction.user.id)

            mlvl = player.get_monster_lvl()

            wolf = Monster(1001, "Волк", mlvl, 100, 11, {"Волчий клык": 0.5, "Волчья шкура": 0.3}, 'https://i.imgur.com/cjOvipe.png')
            wwolf = Monster(1002, "Белый Волк", mlvl, 200, 30, {"Волчий клык": 0.7, "Волчья шкура": 0.5, "Белая шкура": 0.2}, 'https://i.imgur.com/kcPiYNr.png')
            werewolf = Monster(1010, "Вервольф",  mlvl, 150, 25, {"Волчья шкура": 0.5, "Человечина": 0.2}, 'https://i.imgur.com/6pu8XQs.png')
            awerewolf = Monster(1020, "Вервольф в броне", mlvl, 250,  25, {"Волчья шкура": 0.7, "Человечина": 0.3}, 'https://i.imgur.com/wUpilNG.png')
            leader = Leader(1100, "Вервольф-Вожак", 750, 70, "Жуткий вой", "Стальные когти", {"Волчья шкура": 0.6, "Человечина": 0.4, "Амулет": 0.05}, 'https://i.imgur.com/xJ3zOkK.png')

            creatures = [wolf, wwolf, werewolf, awerewolf, leader]
            weights = [10, 25, 30, 45, 15]

            player.curret_monster = random.choices(creatures, weights)[0]

            embed = discord.Embed(title=f"На вас вышел {player.curret_monster.name}", colour=0x8f0000)
            embed.set_image(url=player.curret_monster.img)

            await interaction.response.edit_message(content="",embed=embed,view = Fight())

    @discord.ui.button(row = 4, label="Назад", style=discord.ButtonStyle.primary)
    async def back(self, button, interaction):
        await interaction.response.edit_message(content="Вы вышли в город", embed = None, view = City())

# ================================================================ БОЙ БИЧЕЗ ================================================================

class Battle:
    def __init__(self, player, monster):
        self.player = player
        self.monster = monster

    def player_turn(self):
        if self.monster.health > 0:
            damage = self.player.attack(self.monster)
            if self.monster.health <= 0:
                self.handle_monster_defeat()
            return damage
        return 0

    def monster_turn(self):
        action = random.choice(['attack'] + [spell.__name__ for spell in self.monster.spells])
        if action == 'attack':
            damage = self.monster.attack_player(self.player)
            return f"{self.monster.name} наносит {damage} урона! У вас осталось {self.player.health}"
        else:
            getattr(self.monster, action)(self.player)
            return f"{self.monster.name} использует {action}!"

    def handle_monster_defeat(self):
        if self.player.current_quest is not None:
            self.player.current_quest.update_progress(self.monster)
            if self.player.current_quest.is_completed():
                self.player.money += self.player.current_quest.reward
                self.player.current_quest = None

        dropped_items = self.monster.drop_items()
        inventory.add_items(dropped_items)

        self.player.save()

class Fight(discord.ui.View): 
    @discord.ui.button(row=0, label="Атака", style=discord.ButtonStyle.primary)
    async def attack(self, button, interaction):
        player = players.get(interaction.user.id)
        battle = Battle(player, player.curret_monster)
        player_damage = battle.player_turn()

        if player.curret_monster.health <= 0:
            kill_message = f"\n{player.curret_monster.name} повержен!\nПродолжить путь?"
            player.flee()
            await interaction.response.edit_message(content=kill_message, embed=None, view=NextFight())
        else:
            monster_action = battle.monster_turn()
            embed = discord.Embed(description=f"Вы нанесли {player_damage} урона. У {player.curret_monster.name} осталось {player.curret_monster.health}.\n{monster_action}", colour=0x8f0000)
            embed.set_image(url=player.curret_monster.img)
            await interaction.response.edit_message(embed=embed, view=Fight())


    @discord.ui.button(row = 0, label="Техники", style=discord.ButtonStyle.primary) 
    async def techniques(self, button, interaction):
        pass

    @discord.ui.button(row = 0, label="Защита", style=discord.ButtonStyle.primary) 
    async def guard(self, button, interaction):
        pass

    @discord.ui.button(row = 0,label="Предметы", style=discord.ButtonStyle.primary) 
    async def health(self, button, interaction):
        pass

    @discord.ui.button(row = 0,label="Сбежать", style=discord.ButtonStyle.primary) 
    async def flee(self, button, interaction):
        player = players.get(interaction.user.id)
        player.flee()
        player.save()
        await interaction.response.edit_message(content=f"Вы трусливо сбежали.\n Вы прибыли в город.", embed = None, view = City())


class NextFight(discord.ui.View):
    @discord.ui.button(row = 0, label="Далее", style=discord.ButtonStyle.primary) 
    async def next(self, button, interaction):
        pass

    @discord.ui.button(row = 0, label="В город", style=discord.ButtonStyle.primary) 
    async def ct(self, button, interaction):
        pass

# ================================================================ Подключение ================================================================

@bot.bridge_command(name="join", description='Присоедениться к игре', description_localizations={"ru": "Присоедениться к игре", "en-US": "Join the game", "en-GB": "Join the game", "de": "Dem Spiel beitreten"})
async def join(ctx):

    plid = ctx.author.id
    print(ctx.author.name, "is joined!")
    value = str(plid)

    with open("player_data.json", "r") as file:
        data = json.load(file)

    if value in data:
        player_data = data[value]
        player = Player(ctx.author)
        players[player.user.id] = player
        player.maxhp = player_data.get("maxhp", 0)
        player.health = player_data.get("health", 0)
        player.heal_amount = player_data.get("heal_amount", 0)
        player.money = player_data.get("money", 0)
        player.exp = player_data.get("exp", 0)
        player.next = player_data.get("next", 0)
        player.lvl = player_data.get("lvl", 0)
        player.kills = player_data.get("kills", 0)
        player.inventory = player_data.get("inv", 0)
        player.wins = player_data.get("wins", 0)
        player.loses = player_data.get("loses", 0)

        rep1 = {
            "ru": "\nИ вновь приветствуем!\nВы оказались в городе",
            "en-US": "\nWelcome back!\nYou've come to the city",
            "en-GB": "\nWelcome back!\nYou find yourself in a city",
            "de": "\nWillkommen zurück!\nSie haben sich in einer Stadt wiedergefunden"
            }

        mlvl = player.get_monster_lvl()

        wolf = Wolf(1001, "Волк", mlvl, 100, {wolf_fang: 0.5, wolf_skin: 0.3}, 'https://i.imgur.com/cjOvipe.png')
        wwolf = WhiteWolf(1002, "Белый Волк", mlvl, 200, {wolf_fang: 0.7, white_wolf_skin: 0.5}, 'https://i.imgur.com/kcPiYNr.png')
        werewolf = Werewolf(1010, "Вервольф", mlvl, 150, {wolf_skin: 0.5, man_meat: 0.2}, 'https://i.imgur.com/6pu8XQs.png')
        awerewolf = ArmoredWerewolf(1020, "Вервольф в броне", mlvl, 250, {"Волчья шкура": 0.7, "Человечина": 0.3}, 'https://i.imgur.com/wUpilNG.png')
        leader = Leader(1100, "Вервольф-Вожак", 750, "Жуткий вой", "Стальные когти", {"Волчья шкура": 0.6, "Человечина": 0.4, "Амулет": 0.05}, 'https://i.imgur.com/xJ3zOkK.png')
        beast = Beast(1200, "Зверь из Мосскрита", 1550, "В клочья", "Всплеск адреналина", {"Волчья шкура": 0.6, "Сердце волка": 0.1}, 'https://i.imgur.com/v6wtISO.png')

        if player.current_quest == None:
            creatures = [wolf, wwolf, werewolf, awerewolf, leader, beast]
            weights = [50, 15, 35, 25, 10, 5]

            random_number = random.randint(1, 5)

            random_monster = random.choices(creatures, weights)[0]

            player.current_quest = DailyQuest(random_monster, random_number)

        await ctx.reply(rep1.get(ctx.interaction.locale, rep1['ru']), view=City())        
    else: 
        player = Player(ctx.author)
        players[player.user.id] = player
        rep2 = {
            "ru": "\nПриветствуем новеньких!\nВы оказались в городе",
            "en-US": "\nWelcome newcomers!\nYou're in town.",
            "en-GB": "\nWelcome newcomers!\nYou're in town.",
            "de": "\nWillkommen Neuankömmlinge!\nSie haben sich in einer Stadt eingefunden"
            }
        await ctx.reply(rep2.get(ctx.interaction.locale, rep2['ru']), view=City())

bot.run(f'{bot_key}')