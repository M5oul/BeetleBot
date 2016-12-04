import random
from plugin import Plugin

pizzas = ["Serrano", "Pimienta", "Exotique", "Reine", "Bolognaise",
"Flamenkuche", "BBK", "Farmer", "Orientale", "Arizona", "Gorgonzola",
"Méridionale", "Kebab", "Chicken", "Calzone", "Pepperoni", "Deluxe",
"Reblochonne", "Quatres fromages", "Provençale", "Rustique", "Indienne",
"Margherita"]


class Pizza(Plugin):
    def __init__(self, core):
        super().__init__(core)
        self.register_command('pizza', self.pizza)

    def pizza(self, nb=1):
        """ Usage: !pizza [nb] """
        choices = []
        nb = int(nb)
        if nb > 10:
            return "C'est trop haut"

        for _ in range(nb):
            choices.append(random.choice(pizzas))
        random.choice(pizzas)

        self.send_message_to_room("\n".join(choices))

