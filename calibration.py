from nicegui import ui
from nicegui.elements.mixins.validation_element import ValidationElement
from datetime import date, datetime
import json
import os
import asyncio
import csv
from hx711v0_5_1 import HX711

class ErrorChecker:
    def __init__(self, *elements: ValidationElement) -> None:
        self.elements = elements

    @property
    def no_errors(self) -> bool:
        return all(validation(element.value) for element in self.elements for validation in element.validation.values())

class calibration:
  def __init__(self):
    self.hx = HX711(5, 6)

    self.cal_factor = 0
    self.is_calibration_dialog_open = False

    self.label_cal_factor = None
    self.display_calibration_log = None
    self.input_known_weight = None
    self.button_submit = None

    self.get_cal_factor()

    ui.label('Calibration').classes('text-h3')

    with ui.row(align_items='end').classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-4 q-pr-md').style('row-gap: 0'):
        ui.label('Calibration Factor').classes('text-h5')
        self.label_cal_factor = ui.label(f'{self.cal_factor:.2f}').classes('text-h3 text-right')

        with ui.button(on_click=lambda: self.reset_modal()).props('square unelevated align=left').classes('q-py-md q-mt-md text-bold'):
          ui.icon('settings_backup_restore', size='sm')
          ui.label('Reset Calibration').classes('q-ml-sm')
        
        with ui.button(on_click=lambda: self.calibration_modal()).props('square unelevated align=left').classes('q-py-md q-mt-md text-bold'):
          ui.icon('settings_backup_restore', size='sm')
          ui.label('Start Calibration').classes('q-ml-sm')
      
      ui.column(align_items='stretch').classes('col-4 q-px-md').style('row-gap: 0')

  def get_cal_factor(self):
    calibration_file_path = os.path.join("settings", 'calibration.json')
    
    if not os.path.isfile(calibration_file_path):
      ui.notify(
        f'Path {calibration_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(calibration_file_path, 'r') as file:
      data = json.load(file)
      self.cal_factor = data['cal_factor']
  
  def set_cal_factor(self, cal_factor):
    calibration_file_path = os.path.join("settings", 'calibration.json')
    
    if not os.path.isfile(calibration_file_path):
      ui.notify(
        f'Path {calibration_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(calibration_file_path, 'r+') as file:
      data = json.load(file)
      self.cal_factor = cal_factor
      data['cal_factor'] = self.cal_factor

      file.seek(0)
      json.dump(data, file, indent=4)
      file.truncate()
    
    self.label_cal_factor.set_text(f'{self.cal_factor:.2f}')

  def reset_cal_factor(self, component):
    calibration_file_path = os.path.join("settings", 'calibration.json')
    
    if not os.path.isfile(calibration_file_path):
      ui.notify(
        f'Path {calibration_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(calibration_file_path, 'r+') as file:
      data = json.load(file)
      self.cal_factor = 1.00
      data['cal_factor'] = self.cal_factor

      file.seek(0)
      json.dump(data, file, indent=4)
      file.truncate()
    
    self.label_cal_factor.set_text(f'{self.cal_factor:.2f}')
    component.close()

  def reset_modal(self):
    with ui.dialog().props('persistent backdrop-filter="invert(70%)"') as dialog, ui.card().classes('bg-primary q-pa-none').style('row-gap: 0;'):
      with ui.card_section().classes('full-width'):
        ui.label('Confirm Reset').classes('text-h5 text-white text-bold')

      with ui.card_section().classes('full-screen bg-white'):
        ui.label('Reset calibration factor to 1.00').classes('text-h6')

      with ui.card_actions().props('align="right"').classes('bg-white full-width q-pa-md'):
        ui.button('Cancel', color='grey-7', on_click=lambda: dialog.close()).props('square unelevated')
        ui.button('Reset', color='negative', on_click=lambda: self.reset_cal_factor(dialog)).props('square unelevated')
        # .bind_enabled_from(ErrorChecker(name, std, hysteresis, pack), 'no_errors')

    dialog.open()

  async def calibration_modal(self):
    self.is_calibration_dialog_open = True
    with ui.dialog().props('persistent backdrop-filter="invert(70%)"') as dialog, ui.card().classes('bg-primary q-pa-none').style('width: 400px; row-gap: 0;'):
      with ui.card_section().classes('full-width'):
        ui.label('Calibration').classes('text-h5 text-white text-bold')

      with ui.card_section().classes('bg-white full-width'):
        self.display_calibration_log = ui.column(align_items='stretch').style('row-gap: 0')


      with ui.card_actions().props('align="right"').classes('bg-white full-width q-pa-md'):
        ui.button('Cancel', color='grey-7', on_click=lambda: self.close_dialog(dialog)).props('square unelevated')
        self.button_submit = ui.button('Submit', on_click=lambda: self.create_cal_factor(self.input_known_weight.value, dialog)).props('square unelevated').classes('hidden')
    
    dialog.open()

    await self.handle_display_calibration_log(1)
    await self.handle_display_calibration_log(2)

    # self.is_calibration_dialog_open = False

  def close_dialog(self, component):
    self.is_calibration_dialog_open = False
    component.close()

  async def create_cal_factor(self, known_weight, dialog):
    if (self.input_known_weight.validate()):
      rawBytes = self.hx.getRawBytes()
      longValueWithOffset = self.hx.rawBytesToLong(rawBytes)
      referenceUnit = longValueWithOffset / known_weight
      self.hx.setReferenceUnit(referenceUnit)

      self.set_cal_factor(referenceUnit)

      self.button_submit.props(add='disable')
      await self.handle_display_calibration_log(3)

      dialog.close()

  async def handle_display_calibration_log(self, sequence):
    if not self.is_calibration_dialog_open: return
    
    if (sequence == 1):
      with self.display_calibration_log:
        await asyncio.sleep(1)
        if not self.is_calibration_dialog_open: return
        ui.label('Initialize calibration.')

        await asyncio.sleep(1)
        if not self.is_calibration_dialog_open: return
        ui.label('Place the load cell on a level stable surface.')

        await asyncio.sleep(1)
        if not self.is_calibration_dialog_open: return
        ui.label('Remove any load applied to the load cell.')

        dot_text1 = ui.label()
        
        for _ in range(20):
          current_text = dot_text1.text
          dot_text1.text = f'{current_text}.'
          await asyncio.sleep(0.5)
          if not self.is_calibration_dialog_open: break

        # await self.init_calibration()

    if (sequence == 2):
      with self.display_calibration_log:
        await asyncio.sleep(0.5)
        if not self.is_calibration_dialog_open: return
        ui.label('Initialize complete.')

        await asyncio.sleep(1)
        if not self.is_calibration_dialog_open: return
        ui.label('Place **Known Weight** on the loadcell.')
        
        dot_text2 = ui.label()

        for _ in range(20):
          current_text = dot_text2.text
          dot_text2.text = f'{current_text}.'
          await asyncio.sleep(0.5)
          if not self.is_calibration_dialog_open: break
        
        ui.label('Input the **Known Weight** in grams unit.')
        self.input_known_weight = ui.number(
          'Known Weight',
          validation={
            'This field is required': lambda value: value is not None,
            'This field must be more than 0': lambda value: value > 0,
          }
        ).props('suffix="gr" input-class="text-right"')
        self.button_submit.classes(remove='hidden')

    if (sequence == 3):
      with self.display_calibration_log:
        await asyncio.sleep(0.5)
        if not self.is_calibration_dialog_open: return
        ui.label(f'New calibration factor has been set to: {self.cal_factor}')
        
        await asyncio.sleep(1)



  async def init_calibration(self):
    self.hx.autosetOffset()
    self.hx.setReferenceUnit(1)