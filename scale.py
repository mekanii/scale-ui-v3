from nicegui import ui
from datetime import date
import json

class scale:
  def __init__(self):
    self.part_options = []
    self.part_count = 0
    self.weight = 0

    self.count_pack = 0
    self.count_ok = 0
    self.count_ng = 0
    self.count_ok_session = 0

    self.label_count_pack = None
    self.label_count_ok = None
    self.label_count_ng = None

    self.get_parts()
  
    ui.label('Scale').classes('text-h3')
    with ui.row().classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-4 q-pr-md').style('row-gap: 0'):
        self.label_part_count = ui.label(f'Found {self.part_count} parts').classes('text-h6')

        self.select_part = ui.select(
          label='Select Part',
          options=self.part_options,
          on_change=self.select_part_on_change
        ).props(':option-label="(opt) => opt.label.name"').classes('text-h6').style('height: 50px')

        with ui.button(on_click=self.get_parts_render).props('square unelevated align=left').classes('q-py-md q-mt-lg text-bold'):
          ui.icon('cached', size='md')
          ui.label('Reload').classes('text-h6 q-ml-sm')

        with ui.button(on_click=self.tare).props('square unelevated align=left').classes('q-py-md q-mt-lg text-bold'):
          ui.icon('settings_backup_restore', size='md')
          ui.label('Tare').classes('text-h6 q-ml-sm')

      with ui.column().classes('col-8 items-end q-pl-md q-pr-lg'):
        # self.label_selected_part_key = ui.label('').classes('text-h6').style('font-family: "monofonto"; padding-right: 48px;')
        self.label_selected_part_value = ui.label('').classes('text-h2').style('font-family: "monofonto"; padding-right: 59px;')
        self.label_count_pack = ui.label('').classes('text-h2').style('font-family: "monofonto"')
        self.label_count_ok = ui.label('').classes('text-h2').style('font-family: "monofonto"; padding-right: 59px;')
        self.label_count_ng = ui.label('').classes('text-h2').style('font-family: "monofonto"; padding-right: 59px;')

    with ui.row().classes('full-width'):
      with ui.column(align_items='stretch').classes('col-12 q-pr-lg').style('row-gap: 0'):
        self.label_weight = ui.label('').classes('text-right').style('font-family: "monofonto"; font-size: 128px')

  def get_parts(self):
    with open('settings/part.json', 'r') as file:
      self.part_options = json.load(file)
      self.part_count = len(self.part_options)
  
  def get_parts_render(self):
    self.get_parts()
    self.select_part.set_options(self.part_options)
    self.label_part_count.set_text(f'Found {self.part_count} parts')

  def tare(self):
    print('')

  def select_part_on_change(self):
    # self.label_selected_part_key.set_text('Standard Weight ± Tolerance')
    self.label_selected_part_value.set_text(f'{self.select_part.value["std"]} ± {self.select_part.value["hysteresis"]} {self.select_part.value["unit"]}')
    self.label_count_pack.set_text(f'[{self.count_ok_session} / {self.select_part.value["pack"]}] {self.count_pack} PACK')
    self.label_count_ok.set_text(f'{self.count_ok} OK')
    self.label_count_ng.set_text(f'{self.count_ng} NG')
    self.label_weight.set_text(f'{self.weight} {self.select_part.value["unit"]}')
