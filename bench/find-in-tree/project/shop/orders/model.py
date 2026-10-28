from dataclasses import dataclass, field


@dataclass
class Item:
    name: str
    price: int
    qty: int = 1


@dataclass
class Order:
    number: int
    items: list = field(default_factory=list)
    discount: int = 0

    def subtotal(self):
        return sum(i.price * i.qty for i in self.items)

    def total(self):
        return max(0, self.subtotal() - self.discount)
