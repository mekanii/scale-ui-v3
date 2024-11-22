from dataclasses import dataclass, field

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
  part: Position = field(default_factory=Position)
  date: Position = field(default_factory=Position)
  qty: Position = field(default_factory=Position)

@dataclass
class Layout:
  size: Size = field(default_factory=Size)
  padding: Padding = field(default_factory=Padding)
  position: Label = field(default_factory=Label)