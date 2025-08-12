#!/usr/bin/env python3
# SE Wireless Development Tool (Modbus RTU)
#
# Requires:
#   pip install wxPython pymodbus pyserial
#
# Notes:
# - UI kept the same: "Network Monitor" + "Terminal View"
# - Version tolerant for pymodbus 2.x / 3.x
# - All Modbus reads use keyword args only (no positional),
#   trying 'slave=', then 'unit=', then without unit.

import wx
import wxSerialConfigDialog
import serial
import threading
import time

import pymodbus
from pymodbus.client import ModbusSerialClient

try:
    # pymodbus >= 3.x
    from pymodbus import FramerType
    _HAS_FRAMER = True
    _FRAMER_KW = "framer=FramerType.RTU"
except Exception:
    _HAS_FRAMER = False
    _FRAMER_KW = 'method="rtu"'

# -----------------------------
# IDs (keep as-is; deprecation warnings are harmless)
ID_EXIT                     = wx.NewId()
ID_SETTINGS                 = wx.NewId()
ID_TERM                     = wx.NewId()
ID_HELP                     = wx.NewId()

ID_READ_SERIAL_NUMBER       = wx.NewId()
ID_READ_INVERTER_SN         = wx.NewId()
ID_READ_PRODUCTION_DATE     = wx.NewId()
ID_READ_FW                  = wx.NewId()
ID_READ_HW                  = wx.NewId()
ID_READ_MODEL_NUMBER        = wx.NewId()
ID_READ_MANUFACTURER        = wx.NewId()

ID_READ_AC_INPUT_VOLTAGE    = wx.NewId()
ID_READ_AC_INPUT_CURRENT    = wx.NewId()
ID_READ_AC_INPUT_POWER      = wx.NewId()
ID_READ_OUTPUT_ACTIVE_POWER = wx.NewId()
ID_READ_PV1_INPUT_POWER     = wx.NewId()
ID_READ_PV2_INPUT_POWER     = wx.NewId()
ID_READ_BATTERY_VOLTAGE     = wx.NewId()
ID_READ_BATTERY_SOC         = wx.NewId()
ID_READ_OUTPUT_FREQUENCY    = wx.NewId()
ID_READ_DEVICE_TEMPERATURE  = wx.NewId()

ID_READ_LINE_CHARGE_TOTAL       = wx.NewId()
ID_READ_PV_GENERATION_TOTAL     = wx.NewId()
ID_READ_LOAD_CONSUMPTION_TOTAL  = wx.NewId()
ID_READ_BATTERY_CHARGE_TOTAL    = wx.NewId()
ID_READ_BATTERY_DISCHARGE_TOTAL = wx.NewId()
ID_READ_FROM_GRID_TO_LOAD       = wx.NewId()
ID_READ_OPERATION_HOURS         = wx.NewId()

# -----------------------------
# Terminal settings
NEWLINE_CR   = 0
NEWLINE_LF   = 1
NEWLINE_CRLF = 2

class TerminalSetup:
    def __init__(self):
        self.echo = False
        self.unprintable = False
        self.newline = NEWLINE_CRLF

class TerminalSettingsDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.settings = kwds['settings']
        del kwds['settings']
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.checkbox_echo = wx.CheckBox(self, -1, "Local Echo")
        self.checkbox_unprintable = wx.CheckBox(self, -1, "Show unprintable characters")
        self.radio_box_newline = wx.RadioBox(
            self, -1, "Newline Handling",
            choices=["CR only", "LF only", "CR+LF"],
            majorDimension=0, style=wx.RA_SPECIFY_ROWS
        )
        self.button_ok = wx.Button(self, -1, "OK")
        self.button_cancel = wx.Button(self, -1, "Cancel")

        self.SetTitle("Terminal Settings")
        self.button_ok.SetDefault()

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Input/Output"), wx.VERTICAL)
        sizer_4.Add(self.checkbox_echo, 0, wx.ALL, 4)
        sizer_4.Add(self.checkbox_unprintable, 0, wx.ALL, 4)
        sizer_4.Add(self.radio_box_newline, 0, 0, 0)
        sizer_2.Add(sizer_4, 0, wx.EXPAND, 0)
        sizer_3.Add(self.button_ok, 0, 0, 0)
        sizer_3.Add(self.button_cancel, 0, 0, 0)
        sizer_2.Add(sizer_3, 0, wx.ALL | wx.ALIGN_RIGHT, 4)
        self.SetSizerAndFit(sizer_2)

        self.checkbox_echo.SetValue(self.settings.echo)
        self.checkbox_unprintable.SetValue(self.settings.unprintable)
        self.radio_box_newline.SetSelection(self.settings.newline)

        self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.button_ok.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=self.button_cancel.GetId())

    def OnOK(self, events):
        self.settings.echo = self.checkbox_echo.GetValue()
        self.settings.unprintable = self.checkbox_unprintable.GetValue()
        self.settings.newline = self.radio_box_newline.GetSelection()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, events):
        self.EndModal(wx.ID_CANCEL)

# -----------------------------
# Menubar (same structure)
class seWSNMenubar(wx.Frame):
    def __init__(self, parent):
        parent.seWSNView_menubar = wx.MenuBar()
        parent.SetMenuBar(parent.seWSNView_menubar)

        file_menu = wx.Menu()
        item_exit = file_menu.Append(ID_EXIT, "&Exit", "")
        parent.Bind(wx.EVT_MENU, parent.OnExit, item_exit)
        parent.seWSNView_menubar.Append(file_menu, "&File")

        config_menu = wx.Menu()
        item_settings = config_menu.Append(ID_SETTINGS, "&Port Settings...", "")
        item_term = config_menu.Append(ID_TERM, "&Terminal Settings...", "")
        parent.Bind(wx.EVT_MENU, parent.OnPortSettings, item_settings)
        parent.Bind(wx.EVT_MENU, parent.OnTermSettings, item_term)
        parent.seWSNView_menubar.Append(config_menu, "&Config")

        send_menu = wx.Menu()
        # Identity / Info
        send_menu.Append(ID_READ_SERIAL_NUMBER,       "Get Serial Numbers")
        send_menu.Append(ID_READ_INVERTER_SN,         "Get INVERTER SN")
        send_menu.Append(ID_READ_PRODUCTION_DATE,     "Get Production Date")
        send_menu.Append(ID_READ_FW,                  "Get Firmware Version")
        send_menu.Append(ID_READ_HW,                  "Get Hardware Version")
        send_menu.Append(ID_READ_MODEL_NUMBER,        "Get Model Number")
        send_menu.Append(ID_READ_MANUFACTURER,        "Get Manufacturer")
        send_menu.AppendSeparator()
        # Runtime
        send_menu.Append(ID_READ_AC_INPUT_VOLTAGE,    "Get AC Input Voltage")
        send_menu.Append(ID_READ_AC_INPUT_CURRENT,    "Get AC Input Current")
        send_menu.Append(ID_READ_AC_INPUT_POWER,      "Get AC Input Power")
        send_menu.Append(ID_READ_OUTPUT_ACTIVE_POWER, "Get Output Active Power")
        send_menu.Append(ID_READ_PV1_INPUT_POWER,     "Get PV1 Input Power")
        send_menu.Append(ID_READ_PV2_INPUT_POWER,     "Get PV2 Input Power")
        send_menu.Append(ID_READ_BATTERY_VOLTAGE,     "Get Battery Voltage")
        send_menu.Append(ID_READ_BATTERY_SOC,         "Get Battery SOC")
        send_menu.Append(ID_READ_OUTPUT_FREQUENCY,    "Get Output Frequency")
        send_menu.Append(ID_READ_DEVICE_TEMPERATURE,  "Get Device Temperature")
        send_menu.AppendSeparator()
        # Summary
        send_menu.Append(ID_READ_LINE_CHARGE_TOTAL,       "Get Line Charge Total")
        send_menu.Append(ID_READ_PV_GENERATION_TOTAL,     "Get PV Generation Total")
        send_menu.Append(ID_READ_LOAD_CONSUMPTION_TOTAL,  "Get Load Consumption Total")
        send_menu.Append(ID_READ_BATTERY_CHARGE_TOTAL,    "Get Battery Charge Total")
        send_menu.Append(ID_READ_BATTERY_DISCHARGE_TOTAL, "Get Battery Discharge Total")
        send_menu.Append(ID_READ_FROM_GRID_TO_LOAD,       "Get From Grid To Load")
        send_menu.Append(ID_READ_OPERATION_HOURS,         "Get Operation Hours")
        parent.seWSNView_menubar.Append(send_menu, "&Send")

        help_menu = wx.Menu()
        item_help = help_menu.Append(ID_HELP, "&Help", "")
        parent.Bind(wx.EVT_MENU, parent.OnHelp, item_help)
        parent.seWSNView_menubar.Append(help_menu, "&Help")

# -----------------------------
# Pages
class PageTerminalView(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        self.text_ctrl_output = wx.TextCtrl(
            self, wx.ID_ANY, "",
            style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(self.text_ctrl_output, 1, wx.EXPAND, 0)
        self.SetSizer(s)

class PageNetworkMonitor(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        tc_style = wx.TE_READONLY

        nmSplitter = wx.SplitterWindow(self, id=wx.ID_ANY)
        nmSplitter.SetMinimumPaneSize(250)

        tree_pane = wx.Panel(nmSplitter, id=wx.ID_ANY)
        self.tree_ctrl = wx.TreeCtrl(tree_pane, wx.ID_ANY)
        p1sizer = wx.BoxSizer(wx.VERTICAL)
        p1sizer.Add(self.tree_ctrl, 1, wx.GROW, 0)
        tree_pane.SetSizerAndFit(p1sizer)

        nmstat_pane = wx.Panel(nmSplitter, -1)

        # Device Data
        statdevicesizer = wx.StaticBoxSizer(wx.StaticBox(nmstat_pane, wx.ID_ANY, "Device Data"), wx.VERTICAL)

        def row(label):
            hs = wx.BoxSizer(wx.HORIZONTAL)
            st = wx.StaticText(nmstat_pane, wx.ID_ANY, label)
            hs.Add(st, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
            tc = wx.TextCtrl(nmstat_pane, wx.ID_ANY, style=tc_style)
            hs.Add(tc, 1, 0, 0)
            return hs, tc

        r, self.sernumtxc = row("Serial #")
        statdevicesizer.Add(r, 0, wx.EXPAND, 0)
        r, self.invertsntxc = row("Inverter SN")
        statdevicesizer.Add(r, 0, wx.EXPAND, 0)
        r, self.proddatetxc = row("Production Date")
        statdevicesizer.Add(r, 0, wx.EXPAND, 0)
        r, self.fwversiontxc = row("Firmware Version")
        statdevicesizer.Add(r, 0, wx.EXPAND, 0)
        r, self.hwvertxc = row("HW Version")
        statdevicesizer.Add(r, 0, wx.EXPAND, 0)
        r, self.modnumtxc = row("Model Number")
        statdevicesizer.Add(r, 0, wx.EXPAND, 0)
        r, self.manufacturetxc = row("Manufacturer")
        statdevicesizer.Add(r, 0, wx.EXPAND, 0)

        # Network (runtime) Data
        statnetworksizer = wx.StaticBoxSizer(wx.StaticBox(nmstat_pane, wx.ID_ANY, "Run-time Data"), wx.VERTICAL)
        r, self.acinvolttxc = row("AC Input Voltage")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.acincurrtxc = row("AC Input Current")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.acinpowtxc = row("AC Input Power")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.pvinvolttxc = row("PV Input Voltage")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.pvincurrtxc = row("PV Input Current")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.pvinpowtxc = row("PV Input Power")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.batteryvolttxc = row("Battery Voltage")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.batterysoctxc = row("Battery SOC")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.outfreqtxc = row("Output Frequency")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.temptxc = row("Device Temperature")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)
        r, self.utctmtxc = row("UTC Time")
        statnetworksizer.Add(r, 0, wx.EXPAND, 0)

        # Summary Data
        statsensorsizer = wx.StaticBoxSizer(wx.StaticBox(nmstat_pane, wx.ID_ANY, "Summary Data"), wx.VERTICAL)
        r, self.totalacintxc = row("Total AC Input")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.totalpvintxc = row("Total PV Input")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.totalacouttxc = row("Total AC Output")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.batchgtotaltxc = row("Battery Charge Total")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.batdischgtotaltxc = row("Battery Discharge Total")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.usedenergytotaltxc = row("Used Energy Total")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.hourstxc = row("Operation Hours")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.cyclestxc = row("Charge Cycles")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)
        r, self.maxdailytxc = row("Max Daily Production")
        statsensorsizer.Add(r, 0, wx.EXPAND, 0)

        statussizer = wx.BoxSizer(wx.HORIZONTAL)
        statussizer.Add(statdevicesizer, 1, wx.EXPAND, 0)
        statussizer.Add(statnetworksizer, 1, wx.EXPAND, 0)
        statussizer.Add(statsensorsizer, 1, wx.EXPAND, 0)

        p2sizer = wx.BoxSizer(wx.VERTICAL)
        p2sizer.Add(statussizer, 1, wx.GROW | wx.ALL, 5)
        nmstat_pane.SetSizerAndFit(p2sizer)

        nmSplitter.SplitVertically(tree_pane, nmstat_pane, 1)
        spsizer = wx.BoxSizer(wx.VERTICAL)
        spsizer.Add(nmSplitter, 1, wx.EXPAND, 0)
        self.SetSizerAndFit(spsizer)

# -----------------------------
class seWSNViewLayout(wx.Frame):
    def __init__(self, *args, **kwds):
        wx.Frame.__init__(self, *args, **kwds)
        self.SetTitle("SE Wireless Development Tool (Modbus RTU)")
        self.SetSize((1300, 900))

        # serial object for the config dialog to configure
        self.serial = serial.Serial()
        self.serial.timeout = 1.0

        self.settings = TerminalSetup()

        # Modbus client + guard
        self.mb = None
        self.mb_lock = threading.Lock()
        self.modbus_slave_id = 1  # <-- change if your device uses another unit id

        # Menu bar
        seWSNMenubar(self)

        # Notebook
        p = wx.Panel(self)
        self.nb = wx.Notebook(p)
        self.pageNetMon = PageNetworkMonitor(self.nb)
        self.pageTerminal = PageTerminalView(self.nb)
        self.nb.AddPage(self.pageNetMon, "Network Monitor")
        self.nb.AddPage(self.pageTerminal, "Terminal View")

        nbsizer = wx.BoxSizer()
        nbsizer.Add(self.nb, 1, wx.EXPAND)
        p.SetSizer(nbsizer)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.OnReadSerialNumber,          id=ID_READ_SERIAL_NUMBER)
        self.Bind(wx.EVT_MENU, self.OnReadInverterSN,            id=ID_READ_INVERTER_SN)
        self.Bind(wx.EVT_MENU, self.OnReadProductionDate,        id=ID_READ_PRODUCTION_DATE)
        self.Bind(wx.EVT_MENU, self.OnReadFW,                    id=ID_READ_FW)
        self.Bind(wx.EVT_MENU, self.OnReadHW,                    id=ID_READ_HW)
        self.Bind(wx.EVT_MENU, self.OnReadModelNumber,           id=ID_READ_MODEL_NUMBER)
        self.Bind(wx.EVT_MENU, self.OnReadManufacturer,          id=ID_READ_MANUFACTURER)
        self.Bind(wx.EVT_MENU, self.OnReadACInputVoltage,        id=ID_READ_AC_INPUT_VOLTAGE)
        self.Bind(wx.EVT_MENU, self.OnReadACInputCurrent,        id=ID_READ_AC_INPUT_CURRENT)
        self.Bind(wx.EVT_MENU, self.OnReadACInputPower,          id=ID_READ_AC_INPUT_POWER)
        self.Bind(wx.EVT_MENU, self.OnReadOutputActivePower,     id=ID_READ_OUTPUT_ACTIVE_POWER)
        self.Bind(wx.EVT_MENU, self.OnReadPV1InputPower,         id=ID_READ_PV1_INPUT_POWER)
        self.Bind(wx.EVT_MENU, self.OnReadPV2InputPower,         id=ID_READ_PV2_INPUT_POWER)
        self.Bind(wx.EVT_MENU, self.OnReadBatteryVoltage,        id=ID_READ_BATTERY_VOLTAGE)
        self.Bind(wx.EVT_MENU, self.OnReadBatterySOC,            id=ID_READ_BATTERY_SOC)
        self.Bind(wx.EVT_MENU, self.OnReadOutputFrequency,       id=ID_READ_OUTPUT_FREQUENCY)
        self.Bind(wx.EVT_MENU, self.OnReadDeviceTemperature,     id=ID_READ_DEVICE_TEMPERATURE)
        self.Bind(wx.EVT_MENU, self.OnReadLineChargeTotal,       id=ID_READ_LINE_CHARGE_TOTAL)
        self.Bind(wx.EVT_MENU, self.OnReadPVGenerationTotal,     id=ID_READ_PV_GENERATION_TOTAL)
        self.Bind(wx.EVT_MENU, self.OnReadLoadConsumptionTotal,  id=ID_READ_LOAD_CONSUMPTION_TOTAL)
        self.Bind(wx.EVT_MENU, self.OnReadBatteryChargeTotal,    id=ID_READ_BATTERY_CHARGE_TOTAL)
        self.Bind(wx.EVT_MENU, self.OnReadBatteryDischargeTotal, id=ID_READ_BATTERY_DISCHARGE_TOTAL)
        self.Bind(wx.EVT_MENU, self.OnReadFromGridToLoad,        id=ID_READ_FROM_GRID_TO_LOAD)
        self.Bind(wx.EVT_MENU, self.OnReadOperationHours,        id=ID_READ_OPERATION_HOURS)

        # Window close
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    # ---------- UI helpers
    def UpdatePageTerminal(self, s):
        try:
            self.pageTerminal.text_ctrl_output.AppendText(str(s))
        except Exception:
            pass

    # ---------- Settings / Help / Exit
    def OnExit(self, event):
        self.Close()

    def OnClose(self, event):
        try:
            if self.mb:
                try:
                    if getattr(self.mb, "connected", False):
                        self.mb.close()
                except Exception:
                    self.mb.close()
        except Exception:
            pass
        self.Destroy()

    def OnHelp(self, event):
        message = (
            "Version Information:\n\n"
            f"pymodbus: {getattr(pymodbus, '__version__', '?')}\n"
            f"Framer:   {_FRAMER_KW}\n"
            "Comments: Engineering build (Modbus RTU)\n"
        )
        wx.MessageBox(message, "Help About", wx.OK | wx.ICON_INFORMATION)

    def OnTermSettings(self, event):
        dlg = TerminalSettingsDialog(None, -1, "", settings=self.settings)
        dlg.ShowModal()
        dlg.Destroy()

    # ---------- Modbus setup
    def _parity_char(self, pyserial_parity):
        try:
            from serial import PARITY_NONE, PARITY_EVEN, PARITY_ODD
            if pyserial_parity == PARITY_NONE: return 'N'
            if pyserial_parity == PARITY_EVEN: return 'E'
            if pyserial_parity == PARITY_ODD:  return 'O'
        except Exception:
            pass
        return str(pyserial_parity or 'N')

    def mb_connect_from_current_settings(self):
        try:
            if self.mb:
                try:
                    if getattr(self.mb, "connected", False):
                        self.mb.close()
                except Exception:
                    self.mb.close()
        except Exception:
            pass

        port_str = getattr(self.serial, "portstr", None) or getattr(self.serial, "port", None)

        if _HAS_FRAMER:
            # Newer API (3.x)
            self.mb = ModbusSerialClient(
                port=port_str,
                framer=FramerType.RTU,
                baudrate=self.serial.baudrate,
                bytesize=self.serial.bytesize,
                parity=self._parity_char(self.serial.parity),
                stopbits=self.serial.stopbits,
                timeout=self.serial.timeout or 1.0,
            )
        else:
            # Older API (2.x)
            self.mb = ModbusSerialClient(
                method="rtu",
                port=port_str,
                baudrate=self.serial.baudrate,
                bytesize=self.serial.bytesize,
                parity=self._parity_char(self.serial.parity),
                stopbits=self.serial.stopbits,
                timeout=self.serial.timeout or 1.0,
            )

        ok = self.mb.connect()
        return bool(ok)

    def OnPortSettings(self, event=None):
        """Open the port settings dialog and connect Modbus RTU using those settings."""
        try:
            dlg = wxSerialConfigDialog.SerialConfigDialog(
                self, -1, "",
                show=(wxSerialConfigDialog.SHOW_BAUDRATE
                      | wxSerialConfigDialog.SHOW_FORMAT
                      | wxSerialConfigDialog.SHOW_FLOW),
                serial=self.serial
            )
            if dlg.ShowModal() == wx.ID_OK:
                if self.mb_connect_from_current_settings():
                    self.SetTitle(
                        f"SE Wireless Development Tool (Modbus RTU) on {self.serial.portstr} "
                        f"[{self.serial.baudrate},{self.serial.bytesize}{self.serial.parity}{self.serial.stopbits}]"
                    )
                    self.UpdatePageTerminal("Modbus RTU connected.\n")
                    self.UpdatePageTerminal(f"pymodbus {getattr(pymodbus, '__version__', '?')} using {_FRAMER_KW}\n")
                else:
                    wx.MessageBox(
                        "Failed to connect via Modbus RTU with the selected settings.",
                        "Connection Error", wx.OK | wx.ICON_ERROR
                    )
            dlg.Destroy()
        except Exception as e:
            wx.MessageBox(f"Error in port settings: {e}", "Error", wx.OK | wx.ICON_ERROR)

    # ---------- Version-tolerant read wrapper (keywords only)
    def _call_read(self, method_name, address, count, unit):
        """Call a Modbus read with keyword args only; try 'slave', then 'unit', then without."""
        if not self.mb:
            return None
        fn = getattr(self.mb, method_name, None)
        if not fn:
            return None

        # Try keyword 'slave'
        try:
            return fn(address=address, count=count, slave=unit)
        except TypeError:
            pass

        # Try keyword 'unit'
        try:
            return fn(address=address, count=count, unit=unit)
        except TypeError:
            pass

        # Try without unit (client default)
        try:
            return fn(address=address, count=count)
        except TypeError:
            pass

        # Last resort: only address (count may default to 1 in some builds)
        try:
            return fn(address=address)
        except Exception:
            return None

    def _read_holding(self, address, count=1, unit=None):
        unit = unit or self.modbus_slave_id
        return self._call_read("read_holding_registers", address, count, unit)

    def _read_input(self, address, count=1, unit=None):
        unit = unit or self.modbus_slave_id
        return self._call_read("read_input_registers", address, count, unit)

    def mb_read_holding(self, address, count=1, unit=None):
        if not self.mb:
            wx.MessageBox("Modbus client is not connected.", "Error", wx.OK | wx.ICON_ERROR)
            return None
        with self.mb_lock:
            rr = self._read_holding(address, count, unit)
        if rr is None:
            self.UpdatePageTerminal(f"Read failed (None) at 0x{address:04X}\n")
            return None
        try:
            if rr.isError():
                self.UpdatePageTerminal(f"Modbus error on 0x{address:04X}: {rr}\n")
                return None
        except Exception:
            pass
        # Some older exceptions may be ModbusIOException instances that behave like errors
        if getattr(rr, "registers", None) is None:
            self.UpdatePageTerminal(f"No data returned at 0x{address:04X}: {rr}\n")
            return None
        return rr.registers

    def mb_read_input(self, address, count=1, unit=None):
        if not self.mb:
            wx.MessageBox("Modbus client is not connected.", "Error", wx.OK | wx.ICON_ERROR)
            return None
        with self.mb_lock:
            rr = self._read_input(address, count, unit)
        if rr is None:
            self.UpdatePageTerminal(f"Read failed (None) at 0x{address:04X}\n")
            return None
        try:
            if rr.isError():
                self.UpdatePageTerminal(f"Modbus error on 0x{address:04X}: {rr}\n")
                return None
        except Exception:
            pass
        if getattr(rr, "registers", None) is None:
            self.UpdatePageTerminal(f"No data returned at 0x{address:04X}: {rr}\n")
            return None
        return rr.registers

    # ---------- Basic converters
    def regs_to_u16(self, regs):
        return None if not regs else int(regs[0] & 0xFFFF)

    def regs_to_s16(self, regs):
        if not regs: return None
        v = regs[0] & 0xFFFF
        return v - 0x10000 if v & 0x8000 else v

    def regs_to_u32_be(self, regs):
        if not regs or len(regs) < 2: return None
        return ((regs[0] & 0xFFFF) << 16) | (regs[1] & 0xFFFF)

    def regs_to_ascii(self, regs):
        if not regs: return ""
        b = b"".join(int(r & 0xFFFF).to_bytes(2, "big") for r in regs)
        return b.split(b"\x00", 1)[0].decode("ascii", errors="ignore")

    # ---------- Identity / Info
    def OnReadSerialNumber(self, event):
        regs = self.mb_read_holding(0xC780, 15)  # 15 regs ASCII
        if regs is None: return
        ser = self.regs_to_ascii(regs)
        self.pageNetMon.sernumtxc.SetValue(ser)
        self.UpdatePageTerminal(f"Serial #: {ser}\n")

    def OnReadInverterSN(self, event):
        regs = self.mb_read_holding(0xC78F, 10)  # 10 regs ASCII
        if regs is None: return
        sn = self.regs_to_ascii(regs)
        self.pageNetMon.invertsntxc.SetValue(sn)
        self.UpdatePageTerminal(f"Inverter SN: {sn}\n")

    def OnReadProductionDate(self, event):
        regs = self.mb_read_holding(0xC7A0, 4)  # ASCII (device-specific)
        if regs is None: return
        ds = self.regs_to_ascii(regs)
        self.pageNetMon.proddatetxc.SetValue(ds)
        self.UpdatePageTerminal(f"Production Date: {ds}\n")

    def OnReadFW(self, event):
        regs = self.mb_read_holding(0xC783, 1)
        if regs is None: return
        fw = self.regs_to_u16(regs)
        self.pageNetMon.fwversiontxc.SetValue(str(fw))
        self.UpdatePageTerminal(f"FW version: {fw}\n")

    def OnReadHW(self, event):
        regs = self.mb_read_holding(0xC784, 1)
        if regs is None: return
        hw = self.regs_to_u16(regs)
        self.pageNetMon.hwvertxc.SetValue(str(hw))
        self.UpdatePageTerminal(f"HW version: {hw}\n")

    def OnReadModelNumber(self, event):
        regs = self.mb_read_holding(0xC785, 1)
        if regs is None: return
        model = self.regs_to_u16(regs)
        self.pageNetMon.modnumtxc.SetValue(str(model))
        self.UpdatePageTerminal(f"Model: {model}\n")

    def OnReadManufacturer(self, event):
        regs = self.mb_read_holding(0xC786, 1)
        if regs is None: return
        man = self.regs_to_u16(regs)
        self.pageNetMon.manufacturetxc.SetValue(str(man))
        self.UpdatePageTerminal(f"Manufacturer: {man}\n")

    # ---------- Runtime
    def OnReadACInputVoltage(self, event):
        regs = self.mb_read_holding(0x756A, 1)
        if regs is None: return
        v = self.regs_to_u16(regs)
        self.pageNetMon.acinvolttxc.SetValue(str(v))
        self.UpdatePageTerminal(f"AC Input Voltage: {v}\n")

    def OnReadACInputCurrent(self, event):
        regs = self.mb_read_holding(0x756B, 1)
        if regs is None: return
        a = self.regs_to_u16(regs)
        self.pageNetMon.acincurrtxc.SetValue(str(a))
        self.UpdatePageTerminal(f"AC Input Current: {a}\n")

    def OnReadACInputPower(self, event):
        regs = self.mb_read_holding(0x7571, 1)
        if regs is None: return
        p = self.regs_to_u16(regs)
        self.pageNetMon.acinpowtxc.SetValue(str(p))
        self.UpdatePageTerminal(f"AC Input Power: {p}\n")

    def OnReadOutputActivePower(self, event):
        regs = self.mb_read_holding(0x755E, 1)
        if regs is None: return
        p = self.regs_to_u16(regs)
        self.UpdatePageTerminal(f"Output Active Power: {p}\n")

    def OnReadPV1InputPower(self, event):
        regs = self.mb_read_holding(0x7540, 1)
        if regs is None: return
        p = self.regs_to_u16(regs)
        self.pageNetMon.pvinpowtxc.SetValue(str(p))
        self.UpdatePageTerminal(f"PV1 Input Power: {p}\n")

    def OnReadPV2InputPower(self, event):
        regs = self.mb_read_holding(0x753D, 1)
        if regs is None: return
        p = self.regs_to_u16(regs)
        self.UpdatePageTerminal(f"PV2 Input Power: {p}\n")

    def OnReadBatteryVoltage(self, event):
        regs = self.mb_read_holding(0x7530, 1)
        if regs is None: return
        v = self.regs_to_u16(regs)
        self.pageNetMon.batteryvolttxc.SetValue(str(v))
        self.UpdatePageTerminal(f"Battery Voltage: {v}\n")

    def OnReadBatterySOC(self, event):
        regs = self.mb_read_holding(0x7532, 1)
        if regs is None: return
        soc = self.regs_to_u16(regs)
        self.pageNetMon.batterysoctxc.SetValue(str(soc))
        self.UpdatePageTerminal(f"Battery SOC: {soc}\n")

    def OnReadOutputFrequency(self, event):
        regs = self.mb_read_holding(0x754A, 1)
        if regs is None: return
        f = self.regs_to_u16(regs)
        self.pageNetMon.outfreqtxc.SetValue(str(f))
        self.UpdatePageTerminal(f"Output Frequency: {f}\n")

    def OnReadDeviceTemperature(self, event):
        regs = self.mb_read_holding(0x7579, 1)
        if regs is None: return
        t = self.regs_to_s16(regs)  # often signed
        self.pageNetMon.temptxc.SetValue(str(t))
        self.UpdatePageTerminal(f"Device Temperature: {t}\n")

    # ---------- Summary (2-register u32 big-endian unless your map says otherwise)
    def OnReadLineChargeTotal(self, event):
        regs = self.mb_read_holding(0xCB61, 2)
        if regs is None: return
        val = self.regs_to_u32_be(regs)
        self.pageNetMon.totalacintxc.SetValue(str(val))
        self.UpdatePageTerminal(f"Line Charge Total: {val}\n")

    def OnReadPVGenerationTotal(self, event):
        regs = self.mb_read_holding(0xCB56, 2)
        if regs is None: return
        val = self.regs_to_u32_be(regs)
        self.pageNetMon.totalpvintxc.SetValue(str(val))
        self.UpdatePageTerminal(f"PV Generation Total: {val}\n")

    def OnReadLoadConsumptionTotal(self, event):
        regs = self.mb_read_holding(0xCB58, 2)
        if regs is None: return
        val = self.regs_to_u32_be(regs)
        self.pageNetMon.usedenergytotaltxc.SetValue(str(val))
        self.UpdatePageTerminal(f"Load Consumption Total: {val}\n")

    def OnReadBatteryChargeTotal(self, event):
        regs = self.mb_read_holding(0xCB52, 2)
        if regs is None: return
        val = self.regs_to_u32_be(regs)
        self.pageNetMon.batchgtotaltxc.SetValue(str(val))
        self.UpdatePageTerminal(f"Battery Charge Total: {val}\n")

    def OnReadBatteryDischargeTotal(self, event):
        regs = self.mb_read_holding(0xCB54, 2)
        if regs is None: return
        val = self.regs_to_u32_be(regs)
        self.pageNetMon.batdischgtotaltxc.SetValue(str(val))
        self.UpdatePageTerminal(f"Battery Discharge Total: {val}\n")

    def OnReadFromGridToLoad(self, event):
        regs = self.mb_read_holding(0xCB63, 2)
        if regs is None: return
        val = self.regs_to_u32_be(regs)
        self.UpdatePageTerminal(f"From Grid To Load: {val}\n")

    def OnReadOperationHours(self, event):
        regs = self.mb_read_holding(0xCBB0, 1)
        if regs is None: return
        hours = self.regs_to_u16(regs)
        self.pageNetMon.hourstxc.SetValue(str(hours))
        self.UpdatePageTerminal(f"Operation Hours: {hours}\n")

# -----------------------------
class MyApp(wx.App):
    def OnInit(self):
        self.frame = seWSNViewLayout(None, -1, "")
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()

