#http://www.roguebasin.com/index.php?title=Complete_Roguelike_Tutorial,_using_python%2Blibtcod

#notepad++: run with: "C:\[path]\debug_py.bat" "$(CURRENT_DIRECTORY)" $(FILE_NAME)

import libtcodpy as libtcod
import math
import textwrap
import shelve
import random

###configuration options and initialization

#screen and menus
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 45

LIMIT_FPS = 40

MAP_WIDTH = 80
MAP_HEIGHT = 38

BAR_WIDTH = 20
PANEL_HEIGHT = 10
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

INVENTORY_WIDTH = 50
LEVEL_SCREEN_WIDTH = 40
CHAR_SCREEN_WIDTH = 30

#speeds
PLAYER_SPEED = 2
PLAYER_ATTACK_SPEED = 20
DEFAULT_SPEED = 8
DEFAULT_ATTACK_SPEED = 20
 
#fov configuration
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

#item configuration
HEAL_AMOUNT = 40
MANA_HEAL_AMOUNT = 20

LIGHTNING_RANGE = 50
LIGHTNING_DAMAGE = 40

CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8

HOLY_HAND_GRENADE_RADIUS = 3
HOLY_HAND_GRENADE_DAMAGE = 25

#spell configuration
BLAST_DAMAGE = 5
BLAST_MANA_COST = 5
BLAST_LEVEL = 1
BLAST_RANGE = 8

BLINK_MANA_COST = 10
BLINK_LEVEL = 1
BLINK_RANGE = 20

FREEZE_NUM_TURNS = 10
FREEZE_DAMAGE = 5
FREEZE_RANGE = 8
FREEZE_MANA_COST = 10

STUN_NUM_TURNS = 10
STUN_RANGE = 10

BURN_NUM_TURNS = 10
BURN_DPT = 1 #damage per turn
BURN_RANGE = 5
BURN_MANA_COST = 20

#level up
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150


color_light_ground = libtcod.Color(150, 150, 150)
color_dark_ground = libtcod.Color(75, 75, 75)

libtcod.console_set_custom_font('tiles.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD, 32, 12)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Title Forthcoming: The Game', False, libtcod.RENDERER_SDL)
libtcod.console_map_ascii_codes_to_font(256, 32, 0, 5)
libtcod.console_map_ascii_codes_to_font(256+32, 32, 0, 6)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)

mouse = libtcod.Mouse()
key = libtcod.Key()

mage_tile = 256+32+0 #2nd row, 1st sprite
dead_mage_tile = 256+32+1
skeleton_tile = 256+32+2
dead_skeleton_tile = 256+32+3
orc_tile = 256+32+4
dead_orc_tile = 256+32+5
troll_tile = 256+32+6
dead_troll_tile = 256+32+7

green_potion_tile = 256+2
red_potion_tile = 256+3
blue_potion_tile = 256+4

sword_tile = 256+5
dagger_tile = 256+6
scroll_tile = 256+7
staff_tile = 256+9
wand_tile = 256+10
wood_shield_tile = 256+11
metal_shield_tile = 256+12
bow_tile = 256+13
arrow_tile = 256+14
holy_hand_grenade_tile = 256+17

ice_tile = 256+15
fire_tile = 256+16

wall_tile = 256
ground_tile = 256+1
ladder_tile = 256+8

libtcod.sys_set_fps(LIMIT_FPS)

panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

###base classes

class Object:
	def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=False, speed=DEFAULT_SPEED):
		self.x = x
		self.y = y
		self.char = char
		self.color = color
		self.name = name
		self.blocks = blocks
		self.always_visible = always_visible
		self.speed = speed
		self.wait = 0
				
		self.fighter = fighter
		if self.fighter:
			self.fighter.owner = self
				
		self.ai = ai
		if self.ai:
			self.ai.owner = self
			
		self.item = item
		if self.item:
			self.item.owner = self
			
		self.equipment = equipment
		if self.equipment:
			self.equipment.owner = self
			self.item = Item()
			self.item.owner = self
		
	def move(self, dx, dy):
		if not is_blocked(self.x + dx, self.y +dy):
			self.x += dx
			self.y += dy
		self.wait = self.speed
	
	def move_towards(self, target_x, target_y):
		global fov_map
		path = libtcod.path_new_using_map(fov_map)
		libtcod.path_compute(path, self.x, self.y, target_x, target_y)
		x,y = libtcod.path_get(path, 0)

		if x is None:
			self.move(0, 0)
			
		else:
			dx = int(round(target_x - x))
			dy = int(round(target_y - y))
		
			if dx != 0:
				dx = dx/abs(dx)
			if dy != 0:
				dy = dy/abs(dy)
			
			self.move(dx, dy)
		
		libtcod.path_delete(path)

	def move_away(self, target_x, target_y):
		dx = target_x - self.x
		dy = target_y - self.y
		distance = math.sqrt(dx ** 2 + dy ** 2)
		
		dx = -1 * int(round(dx / distance))
		dy = -1 * int(round(dy / distance))
		
		self.move(dx, dy)
	
	def distance_to(self, other):
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)
		
	def distance(self, x, y):
		return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
	
	def draw(self):
		if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or (self.always_visible and map[self.x][self.y].explored)):
			libtcod.console_set_default_foreground(con, self.color)
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
	
	def send_to_back(self):
		global objects
		objects.remove(self)
		objects.insert(0, self)
	
	def clear(self):
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)
		
class Fighter:
	def __init__(self, hp, defense, power, xp, corpse_icon, death_function=None, mana=0, magic_level=0, ranged_power=0, accuracy=75, range=0, attack_speed=DEFAULT_ATTACK_SPEED):
		self.base_max_hp = hp
		self.hp = hp
		self.base_max_mana = mana
		self.mana = mana
		self.magic_level = magic_level
		self.base_defense = defense
		self.base_power = power
		self.xp = xp
		self.death_function = death_function
		self.corpse_icon = corpse_icon
		self.base_ranged_power = ranged_power
		self.accuracy = accuracy
		self.range = range
		self.attack_speed = attack_speed
		
	def take_damage(self, damage):
		if damage > 0:
			self.hp -= damage
		if self.hp <= 0:
			self.hp = 0
			function = self.death_function
			if function is not None:
				function(self.owner, self.corpse_icon)
			
			if self.owner != player:
				player.fighter.xp += self.xp
				
	def use_mana(self, mana_use):
		self.mana -= mana_use
		if self.mana < 0:
			self.mana = 0
			
	def heal(self, amount):
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp
			
	def gain_mana(self, amount):
		self.mana += amount
		if self.mana > self.max_mana:
			self.mana = self.max_mana
			
	def attack(self, target):
		damage = self.power - target.fighter.defense
		damage = random_normal_int(damage) #makes damage randomly distributed instead of static
		if damage > 0:
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.', libtcod.orange)
			target.fighter.take_damage(damage)
		else:
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!.', libtcod.blue)
		self.owner.wait = self.attack_speed
			
	def ranged_attack(self, target):
		damage = self.ranged_power - target.fighter.defense
		damage = random_normal_int(damage)
		dice = libtcod.random_get_int(0, 0, 100)
		
		if (damage > 0 and dice <= self.accuracy):
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.', libtcod.orange)
			target.fighter.take_damage(damage)
		elif dice > self.accuracy:
			message(self.owner.name.capitalize() + ' attacks and misses!', libtcod.orange)
		else:
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!.', libtcod.blue)
		self.owner.wait = self.attack_speed
		
		
			
	#stats and bonuses
	
	@property
	def power(self):
		bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
		return self.base_power + bonus
		
	@property
	def defense(self):
		bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
		return self.base_defense + bonus
		
	@property
	def max_hp(self):
		bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_hp + bonus
		
	@property
	def max_mana(self):
		bonus = sum(equipment.max_mana_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_mana + bonus
		
	@property
	def ranged_power(self):
		bonus = sum(equipment.ranged_power_bonus for equipment in get_all_equipped(self.owner))
		return self.base_ranged_power + bonus
	
class BasicMonster:
	def take_turn(self):
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)

class RangedMonster:
	def take_turn(self):
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			if monster.distance_to(player) <= 3: #keep distance
				monster.move_away(player.x, player.y) 
			elif monster.distance_to(player) < 2 and player.fighter.hp > 0: #melee attack
				monster.attack(player) 
			elif player.fighter.hp > 0 and monster.distance_to(player) <= monster.fighter.range: #ranged attack
				monster.fighter.ranged_attack(player) 

class ConfusedMonster:
	def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns
		
	def take_turn(self):
		if self.num_turns > 0:
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.num_turns -= 1
		else:
			self.owner.ai = self.old_ai
			message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)
			
class FrozenMonster:
	def __init__(self, old_ai, old_char, num_turns=FREEZE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns
		self.old_char = old_char
		
	def take_turn(self):
		if self.num_turns > 0:
			self.owner.char = ice_tile
			self.owner.move(0, 0)
			self.num_turns -= 1
		else:
			self.owner.ai = self.old_ai
			self.owner.char = self.old_char
			message('The ' + self.owner.name + ' is no longer frozen!', libtcod.red)
			
class StunnedMonster:
	def __init__(self, old_ai, num_turns=STUN_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns
		
	def take_turn(self):
		if self.num_turns > 0:
			self.owner.move(0, 0)
			self.num_turns -= 1
		else:
			self.owner.ai = self.old_ai
			self.owner.char = self.old_char
			message('The ' + self.owner.name + ' is no longer stunned!', libtcod.red)
			
class BurningMonster:
	def __init__ (self, old_ai, old_char, num_turns=BURN_NUM_TURNS, speed=DEFAULT_ATTACK_SPEED):
			self.old_ai = old_ai
			self.num_turns = num_turns
			self.old_char = old_char
			self.speed = speed

	def take_turn(self):
		for object in objects:
			#spread fire to adjacent fighters
			if object.fighter and object.ai and object not in burningmonsters and object.distance_to(self.owner) < 2: #will burn all monsters that are not already on fire (ie in burningmonsters)
				old_ai = object.ai
				old_char = object.char
				object.ai = BurningMonster(old_ai, old_char)
				object.ai.owner = object
				burningmonsters.append(object)
				
		if self.speed > 0:
			self.owner.char = fire_tile
			self.speed -= 1
		elif self.num_turns > 0:
			self.owner.move_towards(player.x, player.y)
			self.owner.fighter.take_damage(BURN_DPT)
			self.speed = DEFAULT_ATTACK_SPEED
			self.num_turns -= 1
		else:
			self.owner.ai = self.old_ai
			self.owner.char = self.old_char
			message('The ' + self.owner.name + ' is no longer burning!', libtcod.red)
			
			burningmonsters.pop(0) #remove monster from list of burning monsters; it can immediately be burned again (remove to keep fire spread down)
			
class Item:
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self):
		if len(inventory) >= 26:
			message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You picked up a ' + self.owner.name + '!', libtcod.green)
			
		#auto-equip picked up equipment if corresponding slot is empty
		equipment = self.owner.equipment
		if equipment and get_equipped_in_slot(equipment.slot)is None:
			equipment.equip()
			
	def use(self):
		if self.owner.equipment:
			self.owner.equipment.toggle_equip()
			return
		if self.use_function is None:
			message('The ' + self.owner.name + ' cannot be used.')
		else:
			if self.use_function() != 'cancelled':
				inventory.remove(self.owner)
	
	def drop(self):
		objects.append(self.owner)
		inventory.remove(self.owner)
		self.owner.x = player.x
		self.owner.y = player.y
		message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
		
		#dequip dropped equipment
		if self.owner.equipment:
			self.owner.equipment.dequip()
		
class Equipment:
	#items that can be equipped
	def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0, max_mana_bonus=0):
		self.slot = slot
		self.is_equipped = False
		self.power_bonus = power_bonus
		self.defense_bonus = defense_bonus
		self.max_hp_bonus = max_hp_bonus
		self.max_mana_bonus = max_mana_bonus
		
	def toggle_equip(self):
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()
			
	def equip(self):
		old_equipment = get_equipped_in_slot(self.slot)
		if old_equipment is not None:
			old_equipment.dequip()

		self.is_equipped = True
		message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
	
	def dequip(self):
		if not self.is_equipped: return
		self.is_equipped = False
		message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)

###map generation
				
class Tile:
	def __init__(self, blocked, block_sight = None):
		self.blocked = blocked
		self.explored = False
		
		if block_sight is None: block_sight = blocked
		self.block_sight = block_sight

class Rect:
		def __init__(self, x, y, w, h):
			self.x1 = x
			self.y1 = y
			self.x2 = x + w
			self.y2 = y + h
			
		def center(self):
			center_x = (self.x1 + self.x2) / 2
			center_y = (self.y1 + self.y2) / 2
			return (center_x, center_y)
			
		def intersect(self, other):
			return (self.x1 <= other.x2 and self.x2 >= other.x1 and
					self.y1 <= other.y2 and self.y2 >= other.y1)
			
def create_room(room):
	global map
	for x in range(room.x1, room.x2 + 1):
		for y in range(room.y1 + 1, room.y2):
			map[x][y].blocked = False
			map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
	global map
	for x in range(min(x1, x2), max(x1, x2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
	global map
	for y in range(min(y1, y2), max(y1, y2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False
	
def make_map():
	global map, objects, ladder
	
	objects = [player]
	
	map = [[Tile(True)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]
	
	rooms = []
	num_rooms = 0
	
	for r in range(MAX_ROOMS):
		w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		x = libtcod.random_get_int(0, 1, MAP_WIDTH - w - 2)
		y = libtcod.random_get_int(0, 1, MAP_HEIGHT - h - 2)
		
		new_room  = Rect(x, y, w, h)
		failed = False
		for other_room in rooms:
			if new_room.intersect(other_room):
				failed = True
				break
		
		if not failed:
			create_room(new_room)
			place_objects(new_room)
			(new_x, new_y) = new_room.center()
			
			if num_rooms == 0:
				player.x = new_x
				player.y = new_y
			else:
				(prev_x, prev_y) = rooms[num_rooms - 1].center()
				if libtcod.random_get_int(0, 0, 1) == 1:
					create_h_tunnel(prev_x, new_x, prev_y)
					create_v_tunnel(prev_y, new_y, new_x)
				
				else:
					create_v_tunnel(prev_y, new_y, prev_x)
					create_h_tunnel(prev_x, new_x, new_y)
			rooms.append(new_room)
			num_rooms +=1
		
	#place ladder in center of last room
	ladder = Object(new_x, new_y, ladder_tile, 'ladder', libtcod.white, always_visible=True)
	objects.append(ladder)
	ladder.send_to_back()

###monsters and items

def random_choice_index(chances):
	dice = libtcod.random_get_int(0, 1, sum(chances))
	
	running_sum = 0
	choice = 0
	for w in chances:
		running_sum += w
		
		if dice <= running_sum:
			return choice
		choice += 1
		
def random_choice(chances_dict):
	chances = chances_dict.values()
	strings = chances_dict.keys()
	
	return strings[random_choice_index(chances)]
	
def random_normal_int(mean, stddev=1):
	#returns Normally distributed value, if stddev == 1, +-1 of the mean 68% of the time, +-2 27% of the time
	return int(round(random.normalvariate(mean, stddev)))
	
def from_dungeon_level(table):
	#returns a value depending on the current dungeon level
	for (value, level) in reversed(table):
		if dungeon_level >= level:
			return value
	return 0
	
def get_equipped_in_slot(slot):
	for obj in inventory:
		if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
			return obj.equipment
	return None
	
def get_all_equipped(obj):
	if obj == player:
		equipped_list = []
		for item in inventory:
			if item.equipment and item.equipment.is_equipped:
				equipped_list.append(item.equipment)
		return equipped_list
	else:
		return [] #other objects have no inventory
			
def place_objects(room):
	
	#max number of monsters per room over time
	max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
	
	#chances of each monster
	monster_chances = {}
	monster_chances['orc'] = 80 #orcs will never not have a chance of appearing
	monster_chances['goblin'] = from_dungeon_level([[10, 1], [30, 3]])
	monster_chances['troll'] = from_dungeon_level([[1, 1], [2, 4]])
	
	#monster generator
	num_monsters = libtcod.random_get_int(0,0,max_monsters)
	for i in range(num_monsters):
		x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
		y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)
		
		if not is_blocked(x, y):
			#monster_chances = {'orc': 80, 'troll': 20}
			choice = random_choice(monster_chances)
			if choice == 'orc':
				fighter_component = Fighter(hp=20, defense=0, power=4, xp=35, corpse_icon=dead_orc_tile, death_function=monster_death)
				ai_component = BasicMonster()
				monster = Object(x, y, orc_tile, 'orc', libtcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
			elif choice == 'troll':
				fighter_component = Fighter(hp=30, defense=1, power=5, xp=100, corpse_icon=dead_troll_tile, death_function=monster_death)
				ai_component=BasicMonster()
				monster = Object(x, y, troll_tile, 'troll', libtcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
			elif choice == 'goblin':
				fighter_component = Fighter(hp=10, defense=0, power=2, ranged_power=4, xp=50, corpse_icon=dead_skeleton_tile, death_function=monster_death, range=8)
				ai_component=RangedMonster()
				monster = Object(x, y, skeleton_tile, 'goblin archer', libtcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
		
		objects.append(monster)
		
	#max items per room over time
	max_items = from_dungeon_level([[1, 1], [2, 4]])
	
	#chance of each item
	item_chances = {}
	item_chances['heal'] = 20
	item_chances['mana'] = 20
	item_chances['lightning'] = from_dungeon_level([[25, 4]])
	item_chances['grenade'] = from_dungeon_level([[20, 6]])
	item_chances['confuse'] = from_dungeon_level([[15, 2]])
	item_chances['sword'] = from_dungeon_level([[10, 6]])
	item_chances['shield'] = from_dungeon_level([[15, 8]])
	item_chances['wand'] = from_dungeon_level([[5, 3]])
	item_chances['staff'] = from_dungeon_level([[5, 6]])
	
		
	#item generator
	num_items = libtcod.random_get_int(0, 0, max_items)
	for i in range(num_items):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		if not is_blocked(x, y):
			choice = random_choice(item_chances)
			
			if choice == 'heal':
				item_component = Item(use_function=cast_heal)
				item = Object(x, y, red_potion_tile, 'healing potion', libtcod.white, item=item_component)
			elif choice =='mana':
				item_component = Item(use_function=cast_mana)
				item = Object(x, y, blue_potion_tile, 'mana potion', libtcod.white, item=item_component)
			elif choice == 'confuse':
				item_component = Item(use_function=cast_confuse)
				item = Object(x, y, scroll_tile, 'confusion scroll', libtcod.white, item=item_component)
			elif choice == 'lightning':
				item_component = Item(use_function=cast_lightning)
				item = Object(x, y, scroll_tile, 'lightning scroll', libtcod.white, item=item_component)
			elif choice == 'grenade':
				item_component = Item(use_function=use_holy_hand_grenade)
				item = Object(x, y, holy_hand_grenade_tile, 'Holy Hand Grenade of Antioch', libtcod.white, item=item_component)
			elif choice == 'sword':
				equipment_component = Equipment(slot='right hand', power_bonus=3)
				item = Object(x, y, sword_tile, 'sword', libtcod.white, equipment=equipment_component)
			elif choice == 'shield':
				equipment_component = Equipment(slot='left hand', defense_bonus=1)
				item = Object(x, y, wood_shield_tile, 'shield', libtcod.white, equipment=equipment_component)
			elif choice == 'wand':
				equipment_component = Equipment(slot='left hand', max_mana_bonus=20)
				item = Object(x, y, wand_tile, 'wand', libtcod.white, equipment=equipment_component)
			elif choice == 'staff':
				equipment_component = Equipment(slot='left hand', max_mana_bonus=40, power_bonus=1)
				item = Object(x, y, staff_tile, 'staff', libtcod.white, equipment=equipment_component)

			item.always_visible = True
			objects.append(item)
			item.send_to_back()
			
#item use functions
			
def cast_heal():
	if player.fighter.hp == player.fighter.max_hp:
		message('You are already at full health.', libtcod.red)
		return 'cancelled'

	message('You heal ' + str(HEAL_AMOUNT) + ' HP.', libtcod.light_violet)
	player.fighter.heal(HEAL_AMOUNT)

def cast_mana():
	if player.fighter.mana == player.fighter.max_mana:
		message('You are already at full mana.', libtcod.red)
		return 'cancelled'
	
	message('You gain ' + str(MANA_HEAL_AMOUNT) + ' mana.', libtcod.light_violet)
	player.fighter.gain_mana(MANA_HEAL_AMOUNT)
	
def cast_lightning():
	monster = closest_monster(LIGHTNING_RANGE)
	if monster is None:
		message('No enemy in range.', libtcod.red)
		return 'cancelled'

	message('A lightning bolt strikes the ' + monster.name + ' with a loud thunder! The damage is ' + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
	monster.fighter.take_damage(LIGHTNING_DAMAGE)
	
def cast_confuse():
	message('Left-click an enemy to confuse it, or right click to cancel.', libtcod.light_cyan)
	monster = target_monster(CONFUSE_RANGE)
	if monster is None: return 'cancelled'
	
	old_ai = monster.ai
	monster.ai = ConfusedMonster(old_ai)
	monster.ai.owner = monster
	message('The eyes of the ' + monster.name + ' look vacant as he starts to stumble around!', libtcod.light_green)
	
def use_holy_hand_grenade():
	message('Left-click a target tile to take out the Holy Pin, or right-click to cancel.', libtcod.light_cyan)
	(x, y) = target_tile()
	if x is None: return 'cancelled'
	message('One, two, five -- THREE!', libtcod.orange)
	
	for obj in objects:
		if obj.distance(x, y) <= HOLY_HAND_GRENADE_RADIUS and obj.fighter:
			message('The ' + obj.name + ' gets blown to tiny bits for ' + str(HOLY_HAND_GRENADE_DAMAGE) + ' hit points.', libtcod.orange)
			obj.fighter.take_damage(HOLY_HAND_GRENADE_DAMAGE)

def is_blocked(x, y):
	if map[x][y].blocked:
		return True
		
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True
	
	return False
	
def closest_monster(max_range):
	closest_enemy = None
	closest_dist = max_range + 10
	
	for object in objects:
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
			dist = player.distance_to(object)
			if dist < closest_dist:
				closest_enemy = object
				closest_dist = dist
	return closest_enemy
	
def target_monster(max_range=None):
	while True:
		(x, y) = target_tile(max_range)
		if x is None:
			return None
		
		for obj in objects:
			if obj.x == x and obj.y == y and obj.fighter and obj != player:
				return obj
	
def target_tile(max_range=None):
	global key, mouse
	while True:
		libtcod.console_flush()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
		render_all()
		
		(x, y) = (mouse.cx, mouse.cy)
		
		if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and (max_range is None or player.distance(x, y) <= max_range)):
			return (x, y)
			
		#rmb or escape key to exit
		if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
			return (None, None)

def player_move_or_attack(dx, dy):
	global fov_recompute
	
	x = player.x + dx
	y = player.y + dy
	
	target = None
	for object in objects:
		if object.fighter and object.x == x and object.y == y:
			target = object
			break
	
	if target is not None:
		player.fighter.attack(target)

	else:
		player.move(dx, dy)
		fov_recompute = True
		
def player_death(player, icon):
	global game_state
	message('You died!', libtcod.red)
	game_state = 'dead'
	
	player.char = icon
	
def monster_death(monster, icon):
	message(monster.name.capitalize() + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.', libtcod.green)
	monster.char = icon
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name
	
	monster.send_to_back()

###spells

def blast():
	message('Left-click an enemy to blast it, or right click to cancel.', libtcod.light_cyan)
	monster = target_monster(BLAST_RANGE)
	
	if monster is None:
		message('No target', libtcod.cyan)
		return 'cancelled'
	
	if player.fighter.mana < BLAST_MANA_COST:
		message('Not enough mana.', libtcod.red)
		return 'cancelled'
		
	else:
		damage = random_normal_int(BLAST_DAMAGE)
		message('You blast the ' + monster.name.capitalize() + ' for ' + str(damage) + ' hit points.', libtcod.light_blue)
		monster.fighter.take_damage(damage)
		player.fighter.mana -= BLAST_MANA_COST
		
def freeze():
	message('Left-click an enemy to freeze it, or right click to cancel.', libtcod.light_cyan)
	monster = target_monster(FREEZE_RANGE)
	
	if monster is None:
		message('No target', libtcod.cyan)
		return 'cancelled'
	
	if player.fighter.mana < FREEZE_MANA_COST:
		message('Not enough mana.', libtcod.red)
		return 'cancelled'
		
	else:
		message('You freeze the ' + monster.name + '!', libtcod.light_green)
		old_ai = monster.ai
		old_char = monster.char
		
		monster.ai = FrozenMonster(old_ai, old_char)
		monster.ai.owner = monster
		player.fighter.mana -= FREEZE_MANA_COST
		
def blink():
	message('Choose a destination tile.', libtcod.light_violet)
	target = target_tile(BLINK_RANGE)
	
	if target[0] is None:
		message('No target', libtcod.cyan)
		return 'cancelled'
	
	if player.fighter.mana < BLINK_MANA_COST:
		message('Not enough mana.', libtcod.red)
		return 'cancelled'
		
	else:
		player.clear()
		player.x = target[0]
		player.y = target[1]
		player.fighter.mana -= BLINK_MANA_COST
		
def burn():
	message('Left-click an enemy to burn it, or right click to cancel.', libtcod.light_cyan)
	monster = target_monster(BURN_RANGE)
	
	if monster is None:
		message('No target', libtcod.cyan)
		return 'cancelled'
	
	if player.fighter.mana < BURN_MANA_COST:
		message('Not enough mana.', libtcod.red)
		return 'cancelled'
		
	else:
		message('You burn the ' + monster.name + '!', libtcod.light_green)
		old_ai = monster.ai
		old_char = monster.char
		
		monster.ai = BurningMonster(old_ai, old_char)
		burningmonsters.append(monster)
		monster.ai.owner = monster
		player.fighter.mana -= BURN_MANA_COST
			

###menus, rendering, key handling, etc
		
def menu(header, options, width):
    global key
    
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')

    #calculate total height for header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height

    #calculate an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)

    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '[' + chr(letter_index) + '] ' + option_text.capitalize()
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    #blit the contents of window to root console
    x = SCREEN_WIDTH / 2 - width / 2
    y = SCREEN_HEIGHT / 2 - height / 2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    libtcod.console_flush()

    while True:
        #check for input in each iteration
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse) 

        index = key.c - ord('a')
        if key.vk == libtcod.KEY_NONE: continue #if nothing is pressed keep looping

        elif key.vk == libtcod.KEY_ENTER and key.lalt:
            #Alt+Enter: toggle fullscreen
            libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

        elif index >= 0 and index < len(options): return index #if an option is chosen return it's index in the options list

        elif index < 0 or index >= len(options): return None #if any other key is pressed close the menu
	
def inventory_menu(header):
	if len(inventory) == 0:
		options = ['Inventory is empty']
	else:
		options = []
		for item in inventory:
			text = item.name
			#additional info
			if item.equipment and item.equipment.is_equipped:
				text = text + ' (on ' + item.equipment.slot + ')'
			options.append(text)
	index = menu(header, options, INVENTORY_WIDTH)
	
	if index is None or len(inventory) == 0: return None
	return inventory[index].item

def render_all():
	global fov_recompute
	
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			visible = libtcod.map_is_in_fov(fov_map, x, y)
			wall = map[x][y].block_sight
			if not visible:
				if map[x][y].explored:
					if wall:
						libtcod.console_put_char_ex(con, x, y, wall_tile, libtcod.grey, color_dark_ground)
					else:
						libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
			else:
				if wall:
					libtcod.console_put_char_ex(con, x, y, wall_tile, libtcod.white, color_light_ground)
				else:
					libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
				map[x][y].explored = True
				
	for object in objects:
		if object != player:
			object.draw()
	player.draw()	
	
	libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
	
	if fov_recompute:
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

	libtcod.console_set_default_foreground(con, libtcod.white)
	
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	
	#messages
	y = 1
	for (line, color) in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1
	
	#health bar
	render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp, libtcod.light_red, libtcod.darker_red)
	
	#mana bar
	render_bar(1, 3, BAR_WIDTH, 'Mana', player.fighter.mana, player.fighter.max_mana, libtcod.light_blue, libtcod.darker_blue)
	
	#current dungeon level
	libtcod.console_print_ex(panel, 1, 5, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon level ' + str(dungeon_level))
	
	#names of objects under mouse
	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
	
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
	
def handle_keys():
	global fov_recompute
	global keys
		
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		#alt+enter toggles fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit'
	
	if game_state == 'playing':
		
		if player.wait > 0:
			player.wait -= 1
			return
		
		#movement keys
		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			player_move_or_attack(0, -1)
			fov_recompute = True
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			player_move_or_attack(0, 1)
			fov_recompute = True
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			player_move_or_attack(-1, 0)
			fov_recompute = True
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			player_move_or_attack(1, 0)
			fov_recompute = True
		elif key.vk == libtcod.KEY_KP7:
			player_move_or_attack(-1, -1)
			fov_recompute = True
		elif key.vk == libtcod.KEY_KP9:
			player_move_or_attack(1, -1)
			fov_recompute = True
		elif key.vk == libtcod.KEY_KP1:
			player_move_or_attack(-1, 1)
			fov_recompute = True
		elif key.vk == libtcod.KEY_KP3:
			player_move_or_attack(1, 1)
			fov_recompute = True
		elif key.vk == libtcod.KEY_KP5:
			pass
			fov_recompute = True
			
		#spell casting
		
		elif key.vk == libtcod.KEY_1:
			if blast() == 'cancelled':
				return 'didnt-take-turn'
				
		elif key.vk == libtcod.KEY_2:
			if freeze() == 'cancelled':
				return 'didnt-take-turn'
				
		elif key.vk == libtcod.KEY_3:
			if blink() == 'cancelled':
				return 'didnt-take-turn'
			fov_recompute = True
			
		elif key.vk == libtcod.KEY_4:
			if burn() == 'cancelled':
				return 'didnt-take-turn'
			fov_recompute = True
				
		#other keys
		else:
			key_char = chr(key.c)
			#pick up item
			if key_char == 'g':
				for object in objects:
					if object.x == player.x and object.y == player.y and object.item:
						object.item.pick_up()
						break
			#show inventory
			if key_char == 'i':
				chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
				if chosen_item is not None:
					chosen_item.use()
			#drop from inventory
			if key_char == 'd':
				chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
				if chosen_item is not None:
					chosen_item.drop()
			#ladder to next level
			if key.vk == libtcod.KEY_ENTER:
				if ladder.x == player.x and ladder.y == player.y:
					next_level()
			
			if key_char == 'c':
				level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
				msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperienece: ' + str(player.fighter.xp) + 
					'\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximumHP: ' + str(player.fighter.max_hp) + 
					'\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense) + '\nMagic: ' + str(player.fighter.magic_level), CHAR_SCREEN_WIDTH)
			
			return 'didnt-take-turn'
	
def get_names_under_mouse():
	global mouse
	(x, y) = (mouse.cx, mouse.cy)
	
	names = [obj.name for obj in objects if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
	names = ', '.join(names)
	return names.capitalize()
	
def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
	bar_width = int(float(value) / maximum * total_width)
	
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
	
	libtcod.console_set_default_background(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
		
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ': ' + str(value) + '/' + str(maximum))
	
def message(new_msg, color = libtcod.white):
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
	
	for line in new_msg_lines:
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]
			
		game_msgs.append( (line, color) )
		
def msgbox(text, width=50):
	menu(text, [], width)

###game loops

def new_game():
	global player, inventory, game_msgs, game_state, dungeon_level, burningmonsters
	
	dungeon_level = 1
	
	fighter_component = Fighter(hp=100, defense=1, power=2, xp=0, mana=50, corpse_icon=dead_mage_tile, death_function=player_death, magic_level=1, attack_speed=PLAYER_ATTACK_SPEED)
	player = Object(0, 0, mage_tile, 'player', libtcod.white, blocks=True, fighter=fighter_component, speed=PLAYER_SPEED)

	player.level = 1

	make_map()
	initialize_fov()
	
	game_state = 'playing'
	inventory = []
	burningmonsters = []
	
	game_msgs = []
	
	message('Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.', libtcod.red)
	
	#initial equipment
	equipment_component = Equipment(slot='right hand', power_bonus=2)
	obj = Object(0, 0, dagger_tile, 'dagger', libtcod.white, equipment=equipment_component)
	inventory.append(obj)
	equipment_component.equip()
	obj.always_visible = True

def initialize_fov():
	global fov_recompute, fov_map
	fov_recompute = True
	
	libtcod.console_clear(con) #reset background to black
	
	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
		
def play_game():
	global key, mouse
	
	player_action = None

	mouse = libtcod.Mouse()
	key = libtcod.Key()
	while not libtcod.console_is_window_closed():
	
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
		player_action = handle_keys()
		render_all()
		
		libtcod.console_flush()
		
		check_level_up()
	
		for object in objects:
			object.clear()
		
		if player_action == 'exit':
			save_game()
			break
			
		if game_state == 'playing': #and player_action != 'didnt-take-turn':
			for object in objects:
				if object.ai:
					if object.wait > 0:
						object.wait -= 1
					else:
						object.ai.take_turn()
				
def check_level_up():
	global PLAYER_SPEED, PLAYER_ATTACK_SPEED
	level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
	if player.fighter.xp >= level_up_xp:
		player.level += 1
		player.fighter.xp -= level_up_xp
		message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)
		
		choice = None
		while choice == None:
			choice = menu('Level up! choose a stat to raise:\n', 
				['Constitution (+20 HP, from ' + str(player.fighter.max_hp) + ')',
				'Strength (+1 attack, from ' + str(player.fighter.power) + ')',
				'Defense (+1 defense, from ' + str(player.fighter.defense) + ')',
				'Agility (Increased speed)',
				'Magic (+20 Mana, from ' + str(player.fighter.max_mana)], LEVEL_SCREEN_WIDTH)
		if choice == 0:
			player.fighter.base_max_hp += 20
		elif choice == 1:
			player.fighter.base_power += 1
		elif choice == 2:
			player.fighter.base_defense += 1
		elif choice == 3:
			PLAYER_SPEED -= 2
			if PLAYER_SPEED < 0:
				PLAYER_SPEED = 0
			PLAYER_ATTACK_SPEED -= 2
			if PLAYER_ATTACK_SPEED < 0:
				PLAYER_ATTACK_SPEED = 0
		elif choice == 4:
			player.fighter.base_max_mana += 20
			player.fighter.magic_level += 1
		
					
def next_level():
	global dungeon_level
	message('You take a moment to rest and recover your strength', libtcod.light_violet)
	player.fighter.heal(player.fighter.max_hp / 2)
	player.fighter.gain_mana(player.fighter.max_mana / 2)
	
	message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
	dungeon_level += 1
	make_map()
	initialize_fov()
					
def main_menu():
	img = libtcod.image_load('menu_background.png')
	
	while not libtcod.console_is_window_closed():
		libtcod.image_blit_2x(img, 0, 0, 0)
		
		libtcod.console_set_default_foreground(0, libtcod.light_yellow)
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER, 'TITLE FORTHCOMING (BETA)')
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-3, libtcod.BKGND_NONE, libtcod.CENTER, 'Results may vary')
		
		choice = menu('', ['Play a new game', 'Continue last game', 'Controls', 'Quit'], 24)
		
		if choice == 0:
			new_game()
			play_game()
		if choice == 1:
			try:
				load_game()
			except:
				msgbox('\n No saved game to load.\n', 24)
				continue
			play_game()
		if choice == 2:
			msgbox('\n Arrow keys or number pad: move/attack \n 1-9: cast spells \n i: inventory \n g: pick up item \n d: drop items \n c: stats \n Enter: climb ladder \n Escape: quit to main menu', 50)
			continue
		elif choice == 3:
			break

def save_game():
	file = shelve.open('savegame', 'n')
	file['map'] = map
	file['objects'] = objects
	file['player_index'] = objects.index(player)
	file['inventory'] = inventory
	file['game_msgs'] = game_msgs
	file['game_state'] = game_state
	file['ladder_index'] = objects.index(ladder)
	file['dungeon_level'] = dungeon_level
	file['burningmonsters'] = burningmonsters
	file.close()

def load_game():
	global map, objects, player, inventory, game_msgs, game_state, ladder, dungeon_level, burningmonsters
	
	file = shelve.open('savegame', 'r')
	map = file['map']
	objects = file['objects']
	player = objects[file['player_index']]
	inventory = file['inventory']
	game_msgs = file['game_msgs']
	game_state = file['game_state']
	ladder = objects[file['ladder_index']]
	dungeon_level = file['dungeon_level']
	burningmonsters = file['burningmonsters']
	file.close()
	
	initialize_fov()
			
main_menu()