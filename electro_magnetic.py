import pygame

PgVector = pygame.math.Vector2
Vector3d = pygame.math.Vector3

class World:
    def __init__(self, size, dt):
        self.size = size
        self.dt = dt

class CircleDrawer:
    def __init__(self, color, text_color, font_size, 
                 font_file, width, antialias=True):
        self.color = pygame.Color(color)
        self.color_text = text_color
        self.width = width
        self.font_size = font_size
        self.font = pygame.font.Font(font_file, self.font_size)
        self.antialias = antialias

    def __call__(self, screen, center, radius, text):
        pygame.draw.circle(screen, self.color, center, radius, self.width)
        text_image = self.font.render(text, self.antialias, self.color_text)
        screen.blit(text_image,
                    (center - PgVector((0.5 * radius, (self.font_size - 2 * radius)))))

class Tracer:
    def __init__(self, color, radius, interval, width):
        self.color = pygame.Color(color)
        self.width = width
        self.interval = interval
        self.radius = radius
        
    def __call__(self, screen, position_list):
        i = 0
        for i in range(0, (len(position_list) -
                           len(position_list)%self.interval), self.interval):
            pos = position_list[i]
            pygame.draw.circle(screen, self.color, (pos[0], pos[1]), self.radius)

class ValueBoard:
    def __init__(self, color, font_size, font_file, pos, antialias=True):
        self.color = pygame.Color(color)
        self.font_size = font_size
        self.font = pygame.font.Font(font_file, font_size)
        self.pos1 = PgVector((pos[0], pos[1]))
        self.pos2 = self.pos1 + 0.8 * PgVector((0, self.font_size))
        self.antialias = antialias
        
    def __call__(self, screen, text1, text2):
        text_image1 = self.font.render(text1, self.antialias, self.color)
        text_image2 = self.font.render(text2, self.antialias, self.color)
        screen.blit(text_image1, self.pos1)
        screen.blit(text_image2, self.pos2)

def integrate_symplectic(pos, vel, force, mass, dt):
    vel_new = vel + force / mass * dt
    pos_new = pos + vel_new * dt
    return pos_new, vel_new

class ChargedParticle:
    def __init__(self, pos, vel, world, radius=10, mass=10,
                 charge_value=10, charge_sign=True, restitution=0.95,
                 drawer=None, tracer=None):

        self.is_alive = True
        self.world = world
        self.drawer = drawer
        self.tracer = tracer

        self.pos = Vector3d((pos[0], pos[1], 0))
        self.list_position = [(pos[0], pos[1], 0)]
        self.vel = Vector3d((vel[0], vel[1], 0))
        self.radius = radius
        self.mass = mass
        self.restitution = restitution
        if charge_sign:
            self.charge = charge_value
            self.text = '+'
        else:
            self.charge = -charge_value
            self.text = '-'
        
        self.total_force = Vector3d((0, 0, 0))

    def update(self):
        self.move()
        self.list_position.append(self.pos)
        self.update_after_move()
        self.total_force = Vector3d((0, 0, 0))

    def draw(self, screen):
        self.drawer(screen, PgVector((self.pos[0], self.pos[1])),
                    self.radius, self.text)
        
    def trace(self, screen):
        self.tracer(screen, self.list_position)
        
    def receive_force(self, force):
        self.total_force += Vector3d(force)

    def update_after_move(self):
        if self.pos[0] < 0 or self.pos[0] > self.world.size[0] \
            or self.pos[1] > self.world.size[1] or self.pos[1] < 0:
            self.is_alive = False

    def move(self):
        self.pos, self.vel = \
            integrate_symplectic(self.pos, self.vel, self.total_force,
                                 self.mass, self.world.dt)

class FixedChargedParticle(ChargedParticle):
    def __init__(self, pos, vel, world, radius=10, mass=10,
                 charge_value=10, charge_sign=True, restitution=0.95, 
                 drawer=None, tracer=None):
        super().__init__(pos, vel, world, radius, mass,
                         charge_value, charge_sign, restitution, drawer, tracer)
        self.vel, self.mass = Vector3d((0, 0, 0)), 1e9

    def move(self):
        pass

def is_charged_particle(actor):
    return isinstance(actor, ChargedParticle)

def compute_lorentz_force(magnetic_field, vel, charge):
    return vel.cross(charge * magnetic_field)

def compute_electric_field_force(electric_field, charge):
    return electric_field * charge

def coulomb_force(constant, p1, p2):
    if p1.pos == p2.pos:
        return None
    direction = p2.pos - p1.pos
    distance = (direction.magnitude())
    unit_vector = direction / distance
    effective_distance = distance - (p1.radius + p2.radius)
    fe = unit_vector * ((constant * p1.charge * p2.charge /
                         (effective_distance ** 2)))
    return fe

def compute_impact_force_between_points(p1, p2, dt, feynman_radius, constant):
    if (p1.pos - p2.pos).magnitude() > p1.radius + p2.radius + feynman_radius:
        return None
    if p1.pos == p2.pos:
        return None
    normal = (p2.pos - p1.pos).normalize()
    v1 = p1.vel.dot(normal)
    v2 = p2.vel.dot(normal)
    if v1 < v2:
        return None
    e = p1.restitution * p2.restitution
    m1, m2 = p1.mass, p2.mass
    f1 = constant * normal * (-(e + 1) * v1 + (e + 1) * v2) / (1/m1 + 1/m2) / dt
    return f1

class CoulombForce:
    def __init__(self, world, actor_list, constant, target_condition=None,
                 drawer=None, tracer=None):
        self.is_alive = True
        self.world = world
        self.actor_list = actor_list
        self.drawer = drawer
        self.constant = constant
        self.tracer = tracer
        
        if target_condition is None:
            self.target_condition = is_charged_particle
        else:
            self.target_condition = target_condition
        
    def update(self):
        self.generate_force()
        
    def draw(self, screen):
        if self.drawer is not None:
            self.drawer(screen)
            
    def trace(self, screen):
        if self.tracer is not None:
            self.tracer(screen)
        
    def generate_force(self):
        plist = [a for a in self.actor_list if self.target_condition(a)]
        n = len(plist)
        for i in range(n):
            for j in range(i+1, n):
                p1, p2 = plist[i], plist[j]
                fe = coulomb_force(self.constant, p1, p2)
                if fe is None:
                    continue
                p2.receive_force(fe)
                p1.receive_force(-fe)

class CollisionResolver:
    def __init__(self, world, actor_list, feynman_radius, constant, 
                 target_condition=None, drawer=None, tracer=None):
        self.is_alive = True
        self.world = world
        self.drawer = drawer
        self.tracer = tracer
        self.feynman_radius = feynman_radius
        self.constant = constant

        self.actor_list = actor_list
        if target_condition is None:
            self.target_condition = is_charged_particle
        else:
            self.target_condition = target_condition

    def update(self):
        self.generate_force()

    def draw(self, screen):
        if self.drawer is not None:
            self.drawer(screen)
            
    def trace(self, screen):
        if self.tracer is not None:
            self.tracer(screen)

    def generate_force(self):
        plist = [a for a in self.actor_list if self.target_condition(a)]
        n = len(plist)
        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = plist[i], plist[j]
                f1 = compute_impact_force_between_points(p1, p2, self.world.dt,
                                                         self.feynman_radius,
                                                         self.constant)
                if f1 is None:
                    continue
                p1.receive_force(f1)
                p2.receive_force(-f1)

class MagneticForce:
    def __init__(self, world, actor_list, MagneticField=(0,0,0),
                 target_condition=None, drawer=None, tracer=None):
        self.world = world
        self.actor_list = actor_list
        self.magnetic_field = Vector3d((MagneticField[0], MagneticField[1],
                                        MagneticField[2]))
        self.drawer = drawer
        self.tracer = tracer
        
        if target_condition is None:
            self.target_condition = is_charged_particle
        else:
            self.target_condition = target_condition
            
    def update(self):
        self.generate_force()
        
    def draw(self, screen):
        text1 = "Magnetic Field Vector:"
        text2 = str(self.magnetic_field)
        self.drawer(screen, text1, text2)
        
    def trace(self, screen):
        if self.tracer is not None:
            self.tracer(screen)
        
    def generate_force(self):
        plist = [a for a in self.actor_list if self.target_condition(a)]
        for p in plist:
            fl = compute_lorentz_force(self.magnetic_field, p.vel, p.charge)
            p.receive_force(fl)
            
class ElectricFieldForce:
    def __init__(self, world, actor_list, ElectricField=(0,0,0),
                 target_condition=None, drawer=None, tracer=None):
        self.world = world
        self.actor_list = actor_list
        self.electric_field = Vector3d(ElectricField[0], ElectricField[1],
                                       ElectricField[2])
        self.drawer = drawer
        self.tracer = tracer
        
        if target_condition is None:
            self.target_condition = is_charged_particle
        else:
            self.target_condition = target_condition
        
    def update(self):
        self.generate_force()
        
    def draw(self, screen):
        text1 = "Electric Field Vector:"
        text2 = str(self.electric_field)
        self.drawer(screen, text1, text2)
            
    def trace(self, screen):
        if self.tracer is not None:
            self.tracer(screen)    
    
    def generate_force(self):
        plist = [a for a in self.actor_list if self.target_condition(a)]
        for p in plist:
            fe = compute_electric_field_force(self.electric_field, p.charge)
            p.receive_force(fe)
            