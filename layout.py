from dataclasses import dataclass

@dataclass
class Size:
  w: float = 0.0
  h: float = 0.0

@dataclass
class Padding:
  t: float = 0.0
  b: float = 0.0
  l: float = 0.0
  r: float = 0.0

@dataclass
class Position:
  x: float = 0.0
  y: float = 0.0

@dataclass
class Label:
  part: Position = Position()
  date: Position = Position()
  qty: Position = Position()

@dataclass
class Layout:
  size: Size = Size()
  padding: Padding = Padding()
  position: Label = Label()