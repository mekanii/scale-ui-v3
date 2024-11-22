from nicegui import ui
from nicegui.elements.mixins.validation_element import ValidationElement
from datetime import date, datetime
from layout import Layout, Size, Padding, Label, Position
from dataclasses import asdict
import cups
import threading
import queue
import json
import os
import time
import asyncio
from print_routines import PrintRoutines

class ErrorChecker:
  def __init__(self, *elements: ValidationElement) -> None:
    self.elements = elements

  @property
  def no_errors(self) -> bool:
    return all(validation(element.value) for element in self.elements for validation in element.validation.values())

class printers:
  def __init__(self):
    self.printers = []
    self.log_options = []
    self.log_count = 0
    
    self.count_try = 0

    self.layout = Layout()


    self.rows = []
    self.columns = [
      {'name': 'jobid', 'label': 'Job ID', 'field': 'jobid', 'required': True, 'align': 'center', 'classes': 'q-table--col-auto-width'},
      {'name': 'time', 'label': 'Time', 'field': 'time', 'required': True, 'align': 'center', 'classes': 'q-table--col-auto-width'},
      {'name': 'part', 'label': 'Part', 'field': 'part', 'required': True, 'align': 'left'},
      {'name': 'qty', 'label': 'Qty', 'field': 'qty', 'required': True, 'align': 'center', 'classes': 'q-table--col-auto-width'},
      {'name': 'state', 'label': 'State', 'field': 'state', 'required': True, 'align': 'left'},
      {'name': 'action', 'label': '', 'field': 'action', 'required': True, 'align': 'right', 'classes': 'q-table--col-auto-width'},
    ]

    self.input_date = None
    self.menu = None
    self.date = None
    self.select_log = None
    self.label_log_count = None
    self.table_log = None

    self.get_printers()
    self.get_print_settings()
    self.get_logs()
    
    ui.label('Printers').classes('text-h3')

    with ui.row(align_items='end').classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-4 q-pr-md').style('row-gap: 0'):
        self.label_log_count = ui.label(f'Found {self.log_count} logs').classes('text-h6 q-mt-md')

        with ui.input('Date Filter').props('readonly').classes('text-h6') as self.input_date:
          with ui.menu().props('no-parent-event') as self.menu:
            with ui.date(on_change=self.get_logs_render).props('range') as self.date:
              with ui.row().classes('justify-end'):
                ui.button('Close', on_click=self.menu.close).props('flat')
          with self.input_date.add_slot('append'):
            ui.icon('highlight_off').on('click', self.clear_input).classes('cursor-pointer q-pr-sm')
            ui.icon('edit_calendar').on('click', self.menu.open).classes('cursor-pointer')

      with ui.column(align_items='stretch').classes('col-4 q-px-md').style('row-gap: 0'):
        self.select_log = ui.select(
          label='Select Log',
          options=self.log_options,
          on_change=self.select_log_on_change
        ).classes('text-h6')

      with ui.column(align_items='stretch').classes('col-4 q-pl-md').style('row-gap: 0'):
        with ui.button(on_click=lambda: self.open_modal()).props('square unelevated align=left').classes('q-py-md text-bold'):
          ui.icon('add_circle_outline', size='sm')
          ui.label('Print Settings').classes('q-ml-sm')
        

    with ui.row().classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-12').style('row-gap: 0'):
        self.table_log = ui.table(title='Print Job', rows=self.rows, columns=self.columns)
        with self.table_log.add_slot('top-right'):
          self.input_filter = ui.input('Search', on_change=lambda: self.filter_table()).props('outlined dense').classes('text-h6')

        self.table_log.add_slot(f'body-cell-action', """
          <q-td :props="props">
            <q-btn @click="$parent.$emit('print', props.row)" icon="print" flat dense color='blue'/>
          </q-td>
        """)
        self.table_log.on('print', lambda e: self.handle_print(e.args['jobid']))
  
  def get_logs(self):
    self.log_options = []
    self.log_count = 0

    if os.path.exists("logs"):
      for filename in os.listdir("logs"):
        if filename.startswith("print-job-") and filename.endswith(".json"):
          self.log_options.append(filename[10:-5])

      self.log_options.sort(reverse=True)

      if (self.date is not None and self.date.value is not None and self.date.value != ''):
        self.log_options = [log for log in self.log_options if datetime.strptime(log, '%Y-%m-%d').date() >= datetime.strptime(self.date.value['from'], '%Y-%m-%d').date()]
        self.log_options = [log for log in self.log_options if datetime.strptime(log, '%Y-%m-%d').date() <= datetime.strptime(self.date.value['to'], '%Y-%m-%d').date()]
        # self.input_date.set_value(f'{self.input_date.value["from"]} to {self.input_date.value["to"]}')
      
      self.log_count = len(self.log_options)

  def get_logs_render(self):
    self.menu.close()
    self.get_logs()

    if (self.date is not None and self.date.value is not None and self.date.value != ''):
      self.input_date.set_value(f'{self.date.value["from"]} to {self.date.value["to"]}')

    if (self.select_log is not None):
      self.select_log.set_options(self.log_options)

    if (self.label_log_count is not None):
      self.label_log_count.set_text(f'Found {self.log_count} logs')

  def clear_input(self):
    self.input_date.set_value(None)
    self.date.set_value(None)

  def select_log_on_change(self):
    log_file_path = os.path.join("logs", f'print-job-{self.select_log.value}.json')
    
    if not os.path.isfile(log_file_path):
      ui.notify(
        f'Log file {log_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(log_file_path, 'r') as log_file:
      data = json.load(log_file)

      self.rows = []
      for entry in data:
        entry["state"] = {
          3: "PENDING",
          4: "HELD",
          5: "PROCESSING",
          6: "STOPPED",
          7: "CANCELED",
          8: "ABORTED",
          9: "COMPLETED"
        }.get(entry["state"], "UNKNOWN")
      
      self.rows = data
      
      self.table_log.rows = self.rows

  def filter_table(self):
    self.table_log.set_filter(self.input_filter.value)

  def get_printers(self):
    conn = cups.Connection()

    printers = conn.getPrinters()

    default_printer = conn.getDefault()

    self.printers = []

    for printer_name, printer_info in printers.items():
      attributes = conn.getPrinterAttributes(printer_name)

      default_paper_size = attributes.get('media-default', 'Unknown')
      color_supported = attributes.get('color-supported', False)
      default_orientation = attributes.get('orientation-requested-default', 'Unknown')

      default_orientation = attributes.get('orientation-requested-default', 'Unknown')

      self.printers.append({
        'name': printer_name,
        'description': printer_info['printer-info'],
        'location': printer_info.get('printer-location', 'Unknown'),
        'default_paper_size': default_paper_size,
        'color_supported': color_supported,
        'default_orientation': default_orientation,
        'is_default': (printer_name == default_printer)
      })

  def get_print_settings(self):
    print_settings_path = os.path.join("settings", 'page.json')
    
    if not os.path.isfile(print_settings_path):
      ui.notify(
        f'Print Settings file {print_settings_path} does not exist.',
        type='negative'
      )
      return
    
    with open(print_settings_path, 'r') as print_settings_file:
      data = json.load(print_settings_file)
      size = Size(**data['size'])
      padding = Padding(**data['padding'])
      label = Label(
          part=Position(**data['position']['part']),
          date=Position(**data['position']['date']),
          qty=Position(**data['position']['qty'])
      )
      self.layout = Layout(size=size, padding=padding, position=label)

  def open_modal(self):
    with ui.dialog().props('persistent backdrop-filter="invert(70%)"') as dialog, ui.card().classes('bg-primary q-pa-none').style('max-width: 80vw; width: 800px; row-gap: 0;'):
      with ui.card_section().classes('full-width'):
        ui.label('Print Settings').classes('text-h5 text-white text-bold')
      with ui.card_section().classes('bg-white full-width'):
        with ui.row().style('column-gap: 0'):
          with ui.column(align_items='stretch').classes('col-12').style('row-gap: 0'):
            self.select_log = ui.select(
              label='Select Printers',
              options=self.printers,
              value=[printer for printer in self.printers if printer['is_default']][0] if any(printer['is_default'] for printer in self.printers) else None,
              on_change=self.select_log_on_change,
              validation={
                'This field is required': lambda value: value is not None and value != ''
              }
            ).props(':option-label="(opt) => opt.label.description"')
        
        with ui.row().style('column-gap: 0'):
          with ui.column(align_items='stretch').classes('col-6 q-pr-sm').style('row-gap: 0'):
            with ui.card().props('flat bordered'):
              with ui.row().classes('full-width').style('column-gap: 0'):
                with ui.column(align_items='stretch').classes('col-12'):
                  ui.label('Label Size').classes('text-caption text-weight-light')

                with ui.column(align_items='stretch').classes('col-6 q-pr-sm'):
                  w = ui.number(
                    'Width',
                    value=self.layout.size.w,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                      'This field must be more than 0': lambda value: value > 0
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')
                
                with ui.column(align_items='stretch').classes('col-6 q-pl-sm'):
                  h = ui.number(
                    'Height',
                    value=self.layout.size.h,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                      'This field must be more than 0': lambda value: value > 0
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')

          with ui.column(align_items='stretch').classes('col-6 q-pl-sm').style('row-gap: 0'):
            with ui.card().props('flat bordered'):
              with ui.row().classes('full-width').style('column-gap: 0'):
                with ui.column(align_items='stretch').classes('col-12'):
                  ui.label('Label Padding').classes('text-caption text-weight-light')

                with ui.column(align_items='stretch').classes('col-6 q-pr-sm'):
                  t = ui.number(
                    'Top',
                    value=self.layout.padding.t,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')
                
                with ui.column(align_items='stretch').classes('col-6 q-pl-sm'):
                  l = ui.number(
                    'Left',
                    value=self.layout.padding.l,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')

                with ui.column(align_items='stretch').classes('col-6 q-pr-sm'):
                  b = ui.number(
                    'Bottom',
                    value=self.layout.padding.b,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')
                
                with ui.column(align_items='stretch').classes('col-6 q-pl-sm'):
                  r = ui.number(
                    'Right',
                    value=self.layout.padding.r,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')

            with ui.card().props('flat bordered').classes('q-mt-md'):
              with ui.row(align_items='top').classes('full-width').style('column-gap: 0'):
                with ui.column(align_items='stretch').classes('col-12'):
                  ui.label('Text Position').classes('text-caption text-weight-light')

                with ui.column(align_items='stretch').classes('col-2 q-pr-sm q-pt-md'):
                  ui.label('Part').classes('text-caption text-weight-light')

                with ui.column(align_items='stretch').classes('col-5 q-px-sm'):
                  part_x = ui.number(
                    'x',
                    value=self.layout.position.part.x,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')
                
                with ui.column(align_items='stretch').classes('col-5 q-pl-sm'):
                  part_y = ui.number(
                    'y',
                    value=self.layout.position.part.y,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')

                with ui.column(align_items='stretch').classes('col-2 q-pr-sm q-pt-md'):
                  ui.label('Date').classes('text-caption text-weight-light')

                with ui.column(align_items='stretch').classes('col-5 q-px-sm'):
                  date_x = ui.number(
                    'x',
                    value=self.layout.position.date.x,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')
                
                with ui.column(align_items='stretch').classes('col-5 q-pl-sm'):
                  date_y = ui.number(
                    'y',
                    value=self.layout.position.date.y,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')

                with ui.column(align_items='stretch').classes('col-2 q-pr-sm q-pt-md'):
                  ui.label('Qty').classes('text-caption text-weight-light')

                with ui.column(align_items='stretch').classes('col-5 q-px-sm'):
                  qty_x = ui.number(
                    'x',
                    value=self.layout.position.qty.x,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')
                
                with ui.column(align_items='stretch').classes('col-5 q-pl-sm'):
                  qty_y = ui.number(
                    'y',
                    value=self.layout.position.qty.y,
                    validation={
                      'This field is required': lambda value: value is not None and value != '',
                    }
                  ).props('input-class="text-right" suffix="mm" outlined dense')

      with ui.card_actions().props('align="right"').classes('bg-white full-width q-pa-md'):
        ui.button('Cancel', color='grey-7', on_click=lambda: dialog.close()).props('square unelevated')
        ui.button(
          'Update',
          on_click=lambda: self.set_print_settings(dialog, w.value, h.value, t.value, b.value, l.value, r.value, part_x.value, part_y.value, date_x.value, date_y.value, qty_x.value, qty_y.value)
        ).props('square unelevated').bind_enabled_from(ErrorChecker(w, h, t, b, l, r, part_x, part_y, date_x, date_y, qty_x, qty_y), 'no_errors')

    dialog.open()

  def set_print_settings(self, component, w, h, t, b, l, r, part_x, part_y, date_x, date_y, qty_x, qty_y):
    component.close()
    print_settings_path = os.path.join("settings", 'page.json')
    
    if not os.path.isfile(print_settings_path):
      ui.notify(
        f'Print Settings file {print_settings_path} does not exist.',
        type='negative'
      )
      return
    
    with open(print_settings_path, 'r+') as print_settings_file:
      self.layout = Layout(
        size=Size(w=float(w), h=float(h)),
        padding=Padding(t=float(t), b=float(b), l=float(l), r=float(r)),
        position=Label(
          part=Position(x=float(part_x), y=float(part_y)),
          date=Position(x=float(date_x), y=float(date_y)),
          qty=Position(x=float(qty_x), y=float(qty_y))
        )
      )

      dict_layout = asdict(self.layout)
      
      print_settings_file.seek(0)
      json.dump(dict_layout, print_settings_file, indent=4)
      print_settings_file.truncate()

      ui.notify(
        f'Print Settings updated successfully.',
        type='positive'
      )

      component.close()

  async def handle_print(self, job_id):
    result_queue = queue.Queue()
    self.count_try = 0
    threading.Thread(target=self.run_print_label, args=(job_id, result_queue)).start()

    await asyncio.sleep(0.1)
    await self.print_dialog(job_id, result_queue)

  def run_print_label(self, job_id, result_queue):
    result = PrintRoutines.reprint_job(job_id)
    result = result_queue.put(result)

  async def print_dialog(self, job_id, result_queue):
    with ui.dialog().props('persistent backdrop-filter="invert(70%)"') as dialog, ui.card():
      with ui.row().classes('full-width').style('column-gap: 0'):
        with ui.column(align_items='center').classes('col-12'):
          ui.label('Printing, please wait...').classes('text-h5')
          ui.spinner('box', size='xl')
          button_cancel = ui.button(
            'Cancel',
            color='negative',
            on_click=lambda: self.cancel_print_job(job_id, dialog)
          ).classes('invisible')
    dialog.open()
    await self.check_print_label_result(dialog, button_cancel, job_id, result_queue)

  async def check_print_label_result(self, dialog, button_cancel, job_id, result_queue):
    try:
      # Try to get the result from the queue
      result = result_queue.get_nowait()
      if result == True:
        self.get_logs()
        self.select_log_on_change()
        dialog.close()
      elif isinstance(result, str):
        dialog.close()
        ui.notify(
          result,
          type='negative'
        )
    except queue.Empty:
      # If the queue is empty, check again after a short delay
      current_try = self.count_try
      self.count_try = current_try + 1
      if self.count_try == 200:
        button_cancel.classes(remove='invisible')
      await asyncio.sleep(0.1)
      await self.check_print_label_result(dialog, button_cancel, job_id, result_queue)

  def cancel_print_job(self, job_id, dialog):
    conn = cups.Connection()
    printer_name = conn.getDefault()
    jobs = conn.getJobs(which_jobs='all', my_jobs=True)

    if not jobs:
      ui.notify(
        f'No print jobs found.',
        type='negative'
      )
      return False
    
    conn.cancelJob(job_id)

    ui.notify(
      f'Job ID {job_id} for printer {printer_name} canceled.',
      type='positive'
    )
    
    dialog.destroy()