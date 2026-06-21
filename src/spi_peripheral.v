/*
 * Copyright (c) 2026 Zhiyuan (Jerry) Jiang
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module spi_peripheral (
    input wire sclk, 
    input wire copi, 
    input wire ncs, 
    input wire clk, 
    input wire rst_n,
    output reg [7:0] en_reg_out_7_0, 
    output reg [7:0] en_reg_out_15_8, 
    output reg [7:0] en_reg_pwm_7_0, 
    output reg [7:0] en_reg_pwm_15_8, 
    output reg [7:0] pwm_duty_cycle

);

localparam max_address = 7'h04;

wire sclk_post_2ff, copi_post_2ff, ncs_post_2ff;

reg sclk_last, ncs_last;

wire sclk_posedge, ncs_posedge, ncs_negedge;

reg [15:0] copi_received;

reg [4:0] bit_counter;

sync_2ff sclk_2ff (
    .in(sclk),
    .clk(clk),
    .out(sclk_post_2ff),
    .rst_n(rst_n)
);

sync_2ff copi_2ff (
    .in(copi),
    .clk(clk),
    .out(copi_post_2ff),
    .rst_n(rst_n)
);

sync_2ff ncs_2ff (
    .in(ncs),
    .clk(clk),
    .out(ncs_post_2ff),
    .rst_n(rst_n)
);

assign sclk_posedge = sclk_post_2ff & ~sclk_last;

assign ncs_posedge = ncs_post_2ff & ~ncs_last;

assign ncs_negedge = ~ncs_post_2ff & ncs_last;

always @(posedge clk) begin
    

    if (~rst_n) begin
        sclk_last <= 1'b0;
        ncs_last <= 1'b0;
        copi_received <= 16'b0;
        bit_counter <= 4'b0;
        en_reg_out_7_0 <= 8'b0;
        en_reg_out_15_8 <= 8'b0;
        en_reg_pwm_7_0 <= 8'b0;
        en_reg_pwm_15_8 <= 8'b0;
        pwm_duty_cycle <= 8'b0;
    end

    else begin

    sclk_last <= sclk_post_2ff;
    ncs_last <= ncs_post_2ff;

    if (ncs_negedge) begin
        bit_counter <= 4'b0;
    end

    if (sclk_posedge && !ncs_post_2ff && !ncs_negedge) begin
        bit_counter <= bit_counter + 1;
        copi_received <= {copi_received[14:0], copi_post_2ff};
    end

    if (ncs_posedge && bit_counter == 16 ) begin

        if (copi_received[15] == 1) begin

            if (copi_received[14:8] <= max_address) begin

                case (copi_received[14:8])
                7'd0: en_reg_out_7_0 <= copi_received[7:0];
                7'd1: en_reg_out_15_8 <= copi_received[7:0];
                7'd2: en_reg_pwm_7_0 <= copi_received[7:0];
                7'd3: en_reg_pwm_15_8 <= copi_received[7:0];
                7'd4: pwm_duty_cycle <= copi_received[7:0];
                endcase

            end
            
        end

        bit_counter <= 4'b0;
    end

end


end


endmodule


module sync_2ff (
    input wire in,
    input wire clk,
    input wire rst_n,
    output wire out
);

reg ff1;
reg ff2;

always @(posedge clk) begin

    if (~rst_n) begin
        ff1 <= 1'b0;
        ff2 <= 1'b0;
    end

    else begin
        ff1 <= in;
        ff2 <= ff1;
    end

end

assign out = ff2;


endmodule