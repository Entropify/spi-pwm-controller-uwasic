# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def wait_for_rising_edge(dut):
    prev = dut.uo_out.value[7]
    while True:
        await ClockCycles(dut.clk, 1)
        curr = dut.uo_out.value & 0x01
        if curr == 1 and prev == 0:
            break
        prev = curr

async def wait_for_falling_edge(dut):
    prev = dut.uo_out.value[7]
    while True:
        await ClockCycles(dut.clk, 1)
        curr = dut.uo_out.value & 0x01
        if curr == 0 and prev == 1:
            break
        prev = curr


async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Starting SPI test...")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reseting chip...")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Starting PWM Frequency test...")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    dut._log.info("Reseting chip...")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Enabling outputs on uo_out[0]")
    dut._log.info("Writing transaction, address 0x00, data 0x01")
    await send_spi_transaction(dut, 1, 0x00, 0x01)

    dut._log.info("Enabling PWM on uo_out[0]")
    dut._log.info("Writing transaction, address 0x02, data 0x01")
    await send_spi_transaction(dut, 1, 0x02, 0x01)

    dut._log.info("Overwriting PWM duty cycle on uo_out[0] as 50% (128/256) to detect rising edge")
    dut._log.info("Writing transaction, address 0x04, data 0x80")
    await send_spi_transaction(dut, 1, 0x04, 0x80)

    dut._log.info("Capturing rising edge 1")
    await wait_for_rising_edge(dut)
    t_rising_edge1 = cocotb.utils.get_sim_time(units="ns")
    dut._log.info(f"Rising edge 1 captured at {t_rising_edge1}ns")

    dut._log.info("Capturing rising edge 2")
    await wait_for_rising_edge(dut)
    t_rising_edge2 = cocotb.utils.get_sim_time(units="ns")
    dut._log.info(f"Rising edge 2 captured at {t_rising_edge2}ns")

    period = t_rising_edge2 - t_rising_edge1

    frequency = (1 / period) * 1e9 # I'm converting GHz to Hz because period was measured in 10^-9 s :)

    assert (3000*0.99 < frequency < 3000*1.01) , f"Expected 3000 Hz, got {frequency:.2f}Hz, {abs((frequency / 3000)-1) * 100:.2f}% error NOT falling within tolerance range of 1%"
    dut._log.info(f"Expected 3000 Hz, got {frequency:.2f}Hz, {abs((frequency / 3000)-1) * 100:.2f}% error falling within tolerance range of 1%")

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):

    dut._log.info("Starting PWM Duty Cycle test...")
    

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    dut._log.info("Reseting chip...")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Enabling outputs on uo_out[0]")
    dut._log.info("Writing transaction, address 0x00, data 0x01")
    await send_spi_transaction(dut, 1, 0x00, 0x01)

    dut._log.info("Enabling PWM on uo_out[0]")
    dut._log.info("Writing transaction, address 0x02, data 0x01")
    await send_spi_transaction(dut, 1, 0x02, 0x01)

    dut._log.info("Overwriting PWM duty cycle on uo_out[0] as 50% (128/256) to detect duty cycle")
    dut._log.info("Writing transaction, address 0x04, data 0x80")
    await send_spi_transaction(dut, 1, 0x04, 0x80)


    dut._log.info("Capturing rising edge 1")
    await wait_for_rising_edge(dut)
    t_rising_edge1 = cocotb.utils.get_sim_time(units="ns")
    dut._log.info(f"Rising edge 1 captured at {t_rising_edge1}ns")

    dut._log.info("Capturing falling edge")
    await wait_for_falling_edge(dut)
    t_falling_edge = cocotb.utils.get_sim_time(units="ns")
    dut._log.info(f"Falling edge captured at {t_falling_edge}ns")

    dut._log.info("Capturing rising edge 2")
    await wait_for_rising_edge(dut)
    t_rising_edge2 = cocotb.utils.get_sim_time(units="ns")
    dut._log.info(f"Rising edge 2 captured at {t_rising_edge2}ns")

    period = t_rising_edge2 - t_rising_edge1

    high_time = t_falling_edge - t_rising_edge1

    duty_cycle = (high_time / period) * 100

    assert (50*0.99 < duty_cycle < 50*1.01) , f"Expected 50% duty cycle, got {duty_cycle:.2f}%, {abs((duty_cycle / 50)-1) * 100:.2f}% error NOT falling within tolerance range of 1%"
    dut._log.info(f"Expected 50% duty cycle, got {duty_cycle:.2f}%, {abs((duty_cycle / 50)-1) * 100:.2f}% error falling within tolerance range of 1%")

    dut._log.info("Overwriting PWM duty cycle on uo_out[0] as 0% (0/256) to detect edge case")
    dut._log.info("Writing transaction, address 0x04, data 0x00")
    await send_spi_transaction(dut, 1, 0x04, 0x00)

    await ClockCycles(dut.clk, 30000)

    for i in range(12):

        assert dut.uo_out[0].value == 0, f"Expected 0 on uo_out[0] in edge case detection #{i+1}, got {dut.uo_out.value}"
        dut._log.info(f"Edge case check #{i+1}/12 passed")
        await ClockCycles(dut.clk, 3000)

    dut._log.info("Overwriting PWM duty cycle on uo_out[0] as 100% (256/256) to detect edge case")
    dut._log.info("Writing transaction, address 0x04, data 0xff")
    await send_spi_transaction(dut, 1, 0x04, 0xff)

    await ClockCycles(dut.clk, 30000)

    for i in range(12):

        assert dut.uo_out[0].value == 1, f"Expected 1 on uo_out[0] in edge case detection #{i+1}, got {dut.uo_out.value}"
        dut._log.info(f"Edge case check #{i+1}/12 passed")
        await ClockCycles(dut.clk, 3000)






    dut._log.info("PWM Duty Cycle test completed successfully")