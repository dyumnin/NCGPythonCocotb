// Code your testbench here
// or browse Examples
module tb;
  
  reg  CLK = 1'b0;
  reg  RST_N=1'b0;

  // action method in_put
  reg  [7 : 0] in_put;
  reg  EN_in_put=1'b1;
  wire RDY_in_put;

  // actionvalue method out_get
  reg  EN_out_get=1'b0;
  wire [7 : 0] out_get;
  wire RDY_out_get;

  // action method configure
  reg  [7 : 0] configure_address;
  reg  [7 : 0] configure_data;
  reg  EN_configure=1'b0;
  wire RDY_configure;

  // value method interrupt
  wire interrupt;
  wire RDY_interrupt;  
  
always #5 CLK=~CLK;
  
  sumofN i1 (CLK,
	      RST_N,

	      in_put,
	      EN_in_put,
	      RDY_in_put,

	      EN_out_get,
	      out_get,
	      RDY_out_get,

	      configure_address,
	      configure_data,
	      EN_configure,
	      RDY_configure,

	      interrupt,
	      RDY_interrupt);
  
  initial
    begin
  	
      configure_address = 8'd1;

      @(negedge CLK)
      RST_N = 1'b1;
      @(posedge CLK)
      fork
          EN_configure=1'b1;
          configure_data = 8'd1; // 6 Integers to be added
      join
      @(negedge CLK)
      configure_address = 8'd1;
      configure_data = 8'd02;

      @(negedge CLK) in_put = 8'h0F; EN_configure=1'b0;
      @(negedge CLK) in_put = 8'h0F;
      @(negedge CLK) in_put = 8'h0F;
      @(negedge CLK) in_put = 8'h0F;
      @(negedge CLK) in_put = 8'h0F;
      @(negedge CLK) in_put = 8'h0F; 
      @(negedge CLK) in_put = 8'h0F; 
      //@(posedge CLK) EN_out_get = 1'b1;
      @(negedge CLK) in_put = 8'h0F; 
      @(negedge CLK) in_put = 8'h0F; 
      @(negedge CLK) in_put = 8'h0F; 
      @(negedge CLK) in_put = 8'h0F; 
     // @(posedge CLK) EN_out_get = 1'b0;
      @(negedge CLK) $finish;      
    end
  
  initial
  begin
    $dumpfile ("Waveform.vcd");
    $dumpvars();
  end
  
endmodule
