from nicegui import ui, app
import pyautogui
from scale import scale
from summary import summary
from parts import parts
from printers import printers
from calibration import calibration

@ui.page('/')
def default_menu():
  ui.navigate.to('/scale')

@ui.page('/scale')
def default_menu():
  drawer(1)
  app.add_static_files('/assets/fonts', 'assets/fonts')
  app.add_static_files('/assets/tones', 'assets/tones')
  ui.add_head_html(r'''
  <style>
  @font-face{
      font-family: "monofonto";
      src: url('/assets/fonts/monofonto.regular.otf');
      font-weight: normal;
      font-style: normal;
  }
  </style>
  ''')
  scale()

@ui.page('/summary')
def default_menu():
  drawer(2)
  summary()

@ui.page('/parts')
def default_menu():
  drawer(3)
  parts()

@ui.page('/printers')
def default_menu():
  drawer(4)
  printers()

@ui.page('/calibration')
def default_menu():
  drawer(5)
  calibration()

def drawer(index):
  with ui.left_drawer(top_corner=True, bottom_corner=True).style('background-color: #E0E0E0; row-gap: 0; padding: 0'):
    with ui.button(
      on_click=lambda: ui.navigate.to('/scale')
    ).props('unelevated square align=left color=grey-7' if index == 1 else 'flat square align=left color=black').classes('q-py-md').style('width: 300px'):
      ui.icon('cast', size='md')
      ui.label('Scale').classes('text-h6 q-ml-md')
    
    with ui.button(
      on_click=lambda: ui.navigate.to('/summary')
    ).props('unelevated square align=left color=grey-7' if index == 2 else 'flat square align=left color=black').classes('q-py-md').style('width: 300px'):
      ui.icon('insert_chart_outlined', size='md')
      ui.label('Summary').classes('text-h6 q-ml-md')
    
    with ui.button(
      on_click=lambda: ui.navigate.to('/parts')
    ).props('unelevated square align=left color=grey-7' if index == 3 else 'flat square align=left color=black').classes('q-py-md').style('width: 300px'):
      ui.icon('list', size='md')
      ui.label('Parts').classes('text-h6 q-ml-md')
    
    with ui.button(
      on_click=lambda: ui.navigate.to('/printers')
    ).props('unelevated square align=left color=grey-7' if index == 4 else 'flat square align=left color=black').classes('q-py-md').style('width: 300px'):
      ui.icon('print', size='md')
      ui.label('Printers').classes('text-h6 q-ml-md')

    with ui.button(
      on_click=lambda: ui.navigate.to('/calibration')
    ).props('unelevated square align=left color=grey-7' if index == 5 else 'flat square align=left color=black').classes('q-py-md').style('width: 300px'):
      ui.icon('ads_click', size='md')
      ui.label('Calibration').classes('text-h6 q-ml-md')

# app.native.window_args['resizable'] = False
app.native.start_args['debug'] = False
app.native.settings['ALLOW_DOWNLOADS'] = True

ui.run(
  title='ScaleUI v3',
  port=1994,
  native=False,
  # window_size=pyautogui.size(),
  # fullscreen=True,
)