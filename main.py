import pygame
import electro_magnetic as emf
Vector3d = pygame.math.Vector3

class ActorFactory:
    def __init__(self, world, actor_list):
        self.world = world
        self.actor_list = actor_list
        
    def create_charged_particle(self, pos, x0, y0, charge_sign=True, fixed=False):
        x, y = pos
        vel = ((x0 - x)/10, (y0 - y)/10, 0)
        mass = 10
        radius = 10
        tracer_radius = 3
        restitution = 0.95
        charge_value = 0.3
        tracer_interval = 5
        charge_sign_color = (29, 53, 87)
        font_size = 30
        font_file = None

        if not fixed:
            ChargedParticleClass = emf.ChargedParticle
            if charge_sign:
                color = (211, 59, 82)
            else:
                color = (29, 115, 139)
        else:
            ChargedParticleClass = emf.FixedChargedParticle
            color = (255, 255, 255)
        
        return ChargedParticleClass(pos, vel, self.world, radius, mass, charge_value,
                              charge_sign, restitution, 
                              emf.CircleDrawer(color, charge_sign_color, font_size,
                                               font_file, width=0),
                              emf.Tracer(color, tracer_radius, tracer_interval,
                                         width=0))

    def generate_coulomb_force(self):
        coulomb_constant = 500000
        return emf.CoulombForce(self.world, self.actor_list, coulomb_constant)
    
    def generate_magnetic_force(self):
        initial_magnetic_field = Vector3d((0,0,0))
        color = (9, 31, 38)
        font_size = 30
        font_file = None
        pos = (self.world.size[0] - 225, 0)
        return emf.MagneticForce(self.world, self.actor_list, initial_magnetic_field, 
                                 drawer=emf.ValueBoard(color, font_size, font_file, 
                                                       pos, antialias=True))
    
    def generate_electric_field_force(self):
        initial_electric_field = Vector3d((0,0,0))
        color = (9, 31, 38)
        font_size = 30
        font_file = None
        pos = (self.world.size[0] - 225, 60)
        return emf.ElectricFieldForce(self.world, self.actor_list, 
                                      initial_electric_field, drawer=emf.ValueBoard(
                                          color, font_size, font_file, pos, 
                                          antialias=True))

    def create_collision_resolver(self):
        feynman_radius = 15
        weak_force_limit = 5
        return emf.CollisionResolver(self.world, self.actor_list, 
                                     feynman_radius, weak_force_limit)
    
    def text_display(self):
        color = (9, 31, 38)
        font_size = 30
        font_file = None
        pos = (0, self.world.size[1] - 30)
        return emf.ValueBoard(color, font_size, font_file, pos)

class AppMain:
    def __init__(self):
        pygame.init()
        width, height = 1200, 800
        self.screen = pygame.display.set_mode((width, height))
        self.actor_list = []
        self.world = emf.World((width, height), dt=1.0)
        self.factory = ActorFactory(self.world, self.actor_list)
        self.magnetic_force = self.factory.generate_magnetic_force()
        self.electric_field_force = self.factory.generate_electric_field_force()
        self.text_display = self.factory.text_display()
        
        self.actor_list.append(self.factory.create_collision_resolver())
        self.actor_list.append(self.factory.generate_coulomb_force())

    def add_particle(self, pos, x0, y0, button):
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            fixed = True
        else:
            fixed = False

        if button == 1:
            charge_sign = True
        elif button == 3:
            charge_sign = False
        else:
            return
        
        p = self.factory.create_charged_particle(pos, x0, y0, charge_sign, fixed)
        self.actor_list.append(p)
    
    def changing_magfield_value(self, button):
        if button == pygame.K_EQUALS:
            self.magnetic_force.magnetic_field += Vector3d((0,0,1))
        elif button ==  pygame.K_MINUS:
            self.magnetic_force.magnetic_field -= Vector3d((0,0,1))
        else:
            return
        
    def changing_elfield_value(self, button):
        if button == pygame.K_UP:
            self.electric_field_force.electric_field += Vector3d((0,1,0))
        elif button == pygame.K_DOWN:
            self.electric_field_force.electric_field -= Vector3d((0,1,0))
        elif button == pygame.K_RIGHT:
            self.electric_field_force.electric_field += Vector3d((1,0,0))
        elif button == pygame.K_LEFT:
            self.electric_field_force.electric_field -= Vector3d((1,0,0))
        else:
            return
        
    def reset(self, button):
        if button == pygame.K_r:
            self.actor_list[:] = []
            self.actor_list.append(self.factory.create_collision_resolver())
            self.actor_list.append(self.factory.generate_coulomb_force())
            self.magnetic_force.magnetic_field = Vector3d((0,0,0))
            self.electric_field_force.electric_field = Vector3d((0,0,0))
        
    def update(self):
        self.magnetic_force.update()
        self.electric_field_force.update()
        for a in self.actor_list:
            a.update()
        self.actor_list[:] = [a for a in self.actor_list if a.is_alive]
                
    def draw(self):
        self.screen.fill(pygame.Color(208, 224, 239))
        self.electric_field_force.draw(self.screen)
        self.magnetic_force.draw(self.screen)
        self.text_display(self.screen, 'Press [r] to reset', '')
        for a in self.actor_list:
            a.trace(self.screen)
            a.draw(self.screen)
        pygame.display.update()
        
    def run(self):
        clock = pygame.time.Clock()
        
        while True:
            frames_per_second = 60
            clock.tick(frames_per_second)
            
            should_quit = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    should_quit = True
                elif event.type == pygame.KEYDOWN:
                    self.changing_magfield_value(event.key)
                    self.changing_elfield_value(event.key)
                    self.reset(event.key)
                    if event.key == pygame.K_ESCAPE:
                        should_quit = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x0, y0 = event.pos
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.add_particle(event.pos, x0, y0, event.button)
            
            if should_quit:
                break

            self.update()
            self.draw()
            
        pygame.quit()
        
if __name__ == "__main__":
    AppMain().run()