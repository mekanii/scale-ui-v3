from nicegui import ui
from nicegui.elements.mixins.validation_element import ValidationElement
from datetime import date, datetime
import json
import os
import csv

class ErrorChecker:
    def __init__(self, *elements: ValidationElement) -> None:
        self.elements = elements

    @property
    def no_errors(self) -> bool:
        return all(validation(element.value) for element in self.elements for validation in element.validation.values())

class parts:
  def __init__(self):
    self.rows = []
    self.columns = [
      {'name': 'name', 'label': 'Part', 'field': 'name', 'required': True, 'align': 'left'},
      {'name': 'std', 'label': 'Standard', 'field': 'std', 'required': True, 'align': 'right'},
      {'name': 'hysteresis', 'label': 'Tolerance', 'field': 'hysteresis', 'required': True, 'align': 'right'},
      {'name': 'unit', 'label': 'Unit', 'field': 'unit', 'required': True, 'align': 'center'},
      {'name': 'pack', 'label': 'Pack', 'field': 'pack', 'required': True, 'align': 'right'}
    ]

    self.table_parts = None
    self.input_filter = None

    self.get_parts()
    
    ui.label('Parts').classes('text-h3')

    with ui.row(align_items='end').classes('full-width').style('column-gap: 0'):
      ui.column(align_items='stretch').classes('col-4 q-pr-md').style('row-gap: 0')
      
      ui.column(align_items='stretch').classes('col-4 q-px-md').style('row-gap: 0')

      with ui.column(align_items='stretch').classes('col-4 q-pl-md').style('row-gap: 0'):
        with ui.button(on_click=lambda: self.open_modal_create()).props('unelevated align=left').classes('q-py-md text-bold'):
          ui.icon('add_circle_outline', size='sm')
          ui.label('Add Parts').classes('q-ml-sm')

    with ui.row().classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-12').style('row-gap: 0'):
        self.table_parts = ui.table(title='Part List', rows=self.rows, columns=self.columns).on('rowClick', lambda e: self.open_modal(e.args[1]))
        with self.table_parts.add_slot('top-right'):
          self.input_filter = ui.input('Search', on_change=lambda: self.filter_table()).props('outlined dense').classes('text-h6')

  def filter_table(self):
    self.table_parts.set_filter(self.input_filter.value)

  def open_modal(self, val):
    with ui.dialog().props('backdrop-filter="invert(70%)"') as dialog, ui.column():
      with ui.button(
        on_click=lambda: self.open_modal_update(dialog, val)
      ).props('rounded unelevated align=left').classes('q-py-md q-pr-lg text-bold'):
        ui.icon('edit_note', size='md'),
        ui.label('modify').classes('text-h6 q-ml-md')
      with ui.button(
        color='negative',
        on_click=lambda: self.open_modal_delete(dialog, val)
      ).props('rounded unelevated align=left').classes('q-py-md q-pr-lg text-bold'):
        ui.icon('remove_circle_outline', size='md'),
        ui.label('delete').classes('text-h6 q-ml-md')

    dialog.open()

  def open_modal_create(self):
    with ui.dialog().props('persistent backdrop-filter="invert(70%)"') as dialog, ui.card().classes('bg-primary q-pa-none').style('width: 400px; row-gap: 0;'):
      with ui.card_section().classes('full-width'):
        ui.label('Form Create').classes('text-h5 text-white text-bold')
      with ui.card_section().classes('bg-white full-width'):
        with ui.column(align_items='stretch').style('row-gap: 0'):
          name = ui.input(
            'Part Name',
            validation={
              'This field is required': lambda value: value is not None and value != ''
            }
          )
          
          std = ui.number(
            'Standard Weight',
            value=0,
            validation={
              'This field is required': lambda value: value is not None,
              'This field must be more than 0': lambda value: value > 0,
            }
          ).props('suffix="gr" input-class="text-right"').classes('q-mt-md')
          ui.button('Get Weight').props('unelevated square')

          hysteresis = ui.number(
            'Tolerance',
            value=0,
            validation={
              'This field is required': lambda value: value is not None,
              'This field must be more than 0': lambda value: value > 0,
            }
          ).props('suffix="gr" input-class="text-right"').classes('q-mt-md')
          
          ui.label('Unit').classes('text-caption text-weight-light').classes('q-mt-md')
          unit = ui.toggle(['gr', 'kg'], value='gr', on_change=lambda e: self.change_input_suffix(e.value, std, hysteresis)).props('spread no-caps square unelevated').style('border: 1px solid #6796cf;')
          
          pack = ui.number(
            'Pack',
            value=1,
            validation={
              'This field is required': lambda value: value is not None,
              'This field must be at least 1': lambda value: value >= 1,
            }
          ).props('input-class="text-right"').classes('q-mt-md')

          # checker = ErrorChecker(name, std, hysteresis, pack)
      
      with ui.card_actions().props('align="right"').classes('bg-white full-width q-pa-md'):
        ui.button('Cancel', color='grey-7', on_click=lambda: dialog.close()).props('square unelevated')
        ui.button(
          'Create',
          on_click=lambda: self.create_part(
            dialog,
            name.value,
            std.value,
            hysteresis.value,
            unit.value,
            pack.value
          )
        ).props('square unelevated').bind_enabled_from(ErrorChecker(name, std, hysteresis, pack), 'no_errors')

    dialog.open()

  def open_modal_update(self, component, val):
    with ui.dialog().props('persistent') as dialog, ui.card().classes('bg-primary q-pa-none').style('width: 400px; row-gap: 0;'):
      with ui.card_section().classes('full-width'):
        ui.label('Form Update').classes('text-h5 text-white text-bold')
      with ui.card_section().classes('bg-white full-width'):
        with ui.column(align_items='stretch').style('row-gap: 0'):
          name = ui.input(
            'Part Name',
            value=val['name'],
            validation={
              'This field is required': lambda value: value is not None and value != ''
            }
          )
          
          std = ui.number(
            'Standard Weight',
            value=val['std'] if val['unit'] == 'gr' else val['std'] * 1000,
            validation={
              'This field is required': lambda value: value is not None,
              'This field must be more than 0': lambda value: value > 0,
            }
          ).props('suffix="gr" input-class="text-right"').classes('q-mt-md')
          ui.button('Get Weight').props('unelevated square')

          hysteresis = ui.number(
            'Tolerance',
            value=val['hysteresis'],
            validation={
              'This field is required': lambda value: value is not None,
              'This field must be more than 0': lambda value: value > 0,
            }
          ).props('suffix="gr" input-class="text-right"' if val["unit"] == "gr" else 'suffix="kg" input-class="text-right"').classes('q-mt-md')
          
          ui.label('Unit').classes('text-caption text-weight-light').classes('q-mt-md')
          unit = ui.toggle(['gr', 'kg'], value=val['unit'], on_change=lambda e: self.change_input_suffix(e.value, std, hysteresis)).props('spread no-caps square unelevated').style('border: 1px solid #6796cf;')
          
          pack = ui.number(
            'Pack',
            value=val['pack'],
            validation={
              'This field is required': lambda value: value is not None,
              'This field must be at least 1': lambda value: value >= 1,
            }
          ).props('input-class="text-right"').classes('q-mt-md')
      
      with ui.card_actions().props('align="right"').classes('bg-white full-width q-pa-md'):
        ui.button('Cancel', color='grey-7', on_click=lambda: component.close()).props('square unelevated')
        ui.button(
          'Update',
          on_click=lambda: self.update_part(
            component,
            val['id'],
            name.value,
            std.value,
            hysteresis.value,
            unit.value,
            pack.value
          )
        ).props('square unelevated').bind_enabled_from(ErrorChecker(name, std, hysteresis, pack), 'no_errors')

    dialog.open()

  def open_modal_delete(self, component, val):
    with ui.dialog().props('persistent') as dialog, ui.card().classes('bg-primary q-pa-none').style('width: 400px; row-gap: 0;'):
      with ui.card_section().classes('full-width'):
        ui.label('Confirm Delete').classes('text-h5 text-white text-bold')
      with ui.card_section().classes('bg-white full-width'):
        with ui.column(align_items='stretch').style('row-gap: 0'):
          ui.input('Part Name', value=val['name']).props('readonly')
          
          ui.number('Standard Weight', value=val['std'] if val['unit'] == 'gr' else val['std'] * 1000).props('readonly suffix="gr" input-class="text-right"').classes('q-mt-md')

          ui.number('Tolerance', value=val['hysteresis']).props('readonly suffix="gr" input-class="text-right"' if val["unit"] == "gr" else 'readonly suffix="kg" input-class="text-right"').classes('q-mt-md')
          
          ui.label('Unit').classes('text-caption text-weight-light').classes('q-mt-md')
          ui.toggle(['gr', 'kg'], value=val['unit']).props('readonly spread no-caps square unelevated').style('border: 1px solid #6796cf;')
          
          ui.number('Pack', value=val['pack']).props('readonly input-class="text-right"').classes('q-mt-md')
      
      with ui.card_actions().props('align="right"').classes('bg-white full-width q-pa-md'):
        ui.button('Cancel', color='grey-7', on_click=lambda: component.close()).props('square unelevated')
        ui.button(
          'Delete',
          color='negative',
          on_click=lambda: self.delete_part(
            component,
            val['id']
          )
        ).props('square unelevated')

    dialog.open()

  def change_input_suffix(self, val, component1, component2):
    # component1.props('readonly suffix="gr" input-class="text-right"' if val == "gr" else 'readonly suffix="kg" input-class="text-right"')
    component2.set_value(component2.value * 1000 if val == 'gr' else component2.value / 1000)
    component2.props('suffix="gr" input-class="text-right"' if val == "gr" else 'suffix="kg" input-class="text-right"')

  def get_parts(self):
    parts_file_path = os.path.join("settings", 'part.json')
    
    if not os.path.isfile(parts_file_path):
      ui.notify(
        f'Path {parts_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(parts_file_path, 'r') as log_file:
      data = json.load(log_file)
      self.rows = data

      # for entry in data:
      #   self.rows.append((
      #     entry['date'],
      #     entry['time'],
      #     entry['part'],
      #     entry['std'],
      #     entry['unit'],
      #     entry['measured'],
      #     f"{entry['hysteresis']:.2f}",
      #     entry['status']
      #   ))

  def create_part(self, component, name, std, hysteresis, unit, pack):
    parts_file_path = os.path.join("settings", "part.json")
    if not os.path.isfile(parts_file_path):
      ui.notify(
        f'Path {parts_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open('settings/part.json', 'r+') as file:
      data = json.load(file)

      last_id = data[-1]['id'] if data else 0
      new_id = last_id + 1

      new_data = {
          "id": new_id,
          "name": name,
          "std": float(std),
          "hysteresis": float(hysteresis),
          "unit": unit,
          "pack": int(pack)
      }
      data.append(new_data)

      file.seek(0)
      json.dump(data, file, indent=4)
      file.truncate()

      self.rows = data
      self.table_parts.rows = data

      ui.notify(
        f'Part created successfully.',
        type='positive'
      )

    component.close()

  def update_part(self, component, id, name, std, hysteresis, unit, pack):
    parts_file_path = os.path.join("settings", "part.json")
    if not os.path.isfile(parts_file_path):
      ui.notify(
        f'Path {parts_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(parts_file_path, 'r+') as file:
      data = json.load(file)

      for part in data:
        if part['id'] == id:
          part['name'] = name
          part['std'] = float(std) if unit == 'gr' else float(std) / 1000
          part['hysteresis'] = float(hysteresis)
          part['unit'] = unit
          part['pack'] = int(pack)
          break
      else:
        ui.notify(
          f'Part with id {id} not found.',
          type='negative'
        )
        return
      
      file.seek(0)
      json.dump(data, file, indent=4)
      file.truncate()

      self.rows = data
      self.table_parts.rows = data

      ui.notify(
        f'Part with id {id} updated successfully.',
        type='positive'
      )

    component.close()

  def delete_part(self, component, id):
    parts_file_path = os.path.join("settings", "part.json")
    if not os.path.isfile(parts_file_path):
      ui.notify(
        f'Path {parts_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(parts_file_path, 'r+') as file:
      data = json.load(file)

      for part in data:
        if part['id'] == id:
          data.remove(part)
          break
      else:
        ui.notify(
          f'Part with id {id} not found.',
          type='negative'
        )
        return
      
      file.seek(0)
      json.dump(data, file, indent=4)
      file.truncate()

      self.rows = data
      self.table_parts.rows = data

      ui.notify(
        f'Part with id {id} deleted successfully.',
        type='positive'
      )

    component.close()