//==============================================================================
// mda_pkg
//
// Project-wide parameters, types and decode-class constants for the Minimalist
// Deterministic Architecture (MDA).
//
// Scope
//   Contents of this package: memory and datapath sizes, common types, the
//   internal decode classes used between pipeline modules, and the names and
//   values of the Stage B interfaces (pins, configuration packing, loader).
//
//   Contents of mda_isa_pkg instead: opcodes, funct codes, reserved-field
//   masks, flag indices and fault causes. That package is generated from
//   tools/isa/isa.yaml, the single source of truth for the instruction
//   encoding.
//
// Usage
//   import mda_pkg::*;
//   import mda_isa_pkg::*;
//   The two packages declare no common identifier; tools/isa/check_names.py
//   verifies this.
//
// Conventions
//   - Sizes and widths use spelled-out UPPER_CASE names (DATA_WIDTH,
//     IMEM_ADDR_WIDTH, DMEM_SIZE_BYTES).
//   - Types use PascalCase (Word, Instruction, PcAddr).
//   - Constant groups carry a prefix (ALU_*, BR_*, MEM_*, WATCH_*, OSRC_*).
//   - Constants are typed localparams over typedef'd logic vectors. Enumerated
//     types are not used, so the package does not depend on enumeration
//     support in any simulation or synthesis frontend of the toolchain.
//
// Sections
//   [1] Sizes
//   [2] Types
//   [3] Stage A decode classes
//   [4] Stage B interfaces
//==============================================================================

package mda_pkg;

    //--------------------------------------------------------------------------
    // [1] Sizes
    //     Memory sizes are defined here and nowhere else.
    //--------------------------------------------------------------------------
    localparam int NUM_THREADS          = 3;                    // hardware threads (barrel slots)
    localparam int DATA_WIDTH           = 32;                   // data word width in bits
    localparam int INSTR_WIDTH          = 16;                   // instruction width in bits
    localparam int REG_ADDR_WIDTH       = 3;                    // register address width, 8 GPRs per thread
    localparam int NUM_REGS             = 1 << REG_ADDR_WIDTH;  // GPRs per thread
    localparam int FLAGS_WIDTH          = 16;                   // flag slots per thread

    // Instruction memory: 1024 x 16 macro. The PC counts halfwords and wraps.
    // The 10-bit jnl offset reaches the whole memory only while
    // IMEM_ADDR_WIDTH <= 10.
    localparam int IMEM_ADDR_WIDTH      = 10;
    localparam int IMEM_SIZE_HALFWORDS  = 1 << IMEM_ADDR_WIDTH;

    // Data memory: 256 x 32 macro (1 KB), byte addressed by the core.
    localparam int DMEM_ADDR_WIDTH      = 8;                    // word index width
    localparam int DMEM_SIZE_WORDS      = 1 << DMEM_ADDR_WIDTH;
    localparam int DMEM_SIZE_BYTES      = DMEM_SIZE_WORDS * 4;
    localparam int DMEM_BYTE_ADDR_WIDTH = DMEM_ADDR_WIDTH + 2;  // byte address bits inside the memory

    //--------------------------------------------------------------------------
    // [2] Types
    //--------------------------------------------------------------------------
    typedef logic [DATA_WIDTH-1:0]      Word;           // data word
    typedef logic [INSTR_WIDTH-1:0]     Instruction;    // instruction halfword
    typedef logic [IMEM_ADDR_WIDTH-1:0] PcAddr;         // program counter, halfword units
    typedef logic [REG_ADDR_WIDTH-1:0]  RegAddr;        // register address within a thread
    typedef logic [NUM_THREADS-1:0]     ThreadSel;      // one-hot thread select
    typedef logic [FLAGS_WIDTH-1:0]     Flags;          // flag view of one thread
    typedef logic [DMEM_ADDR_WIDTH-1:0] DmemWordAddr;   // data memory word index
    typedef logic [2:0]                 Cause;          // fault cause code (CAUSE_* in mda_isa_pkg)

    localparam Instruction NOP_INSTR     = 16'h0011;    // jnl 0, the canonical no-operation
    localparam Instruction ILLEGAL_INSTR = 16'hFFFF;    // reserved rpin encoding, used as a fill value

    //--------------------------------------------------------------------------
    // [3] Stage A decode classes
    //     Internal signals between decoder, execute and write-back logic.
    //--------------------------------------------------------------------------

    // ALU operation.
    // For the eight register operations the code equals the RR funct code
    // (add 0, xor 1, shl 2, shr 3, cmp 4, cmpa 5, and 6, or 7). The RI-A funct
    // codes 0 to 3 map to add, xor, shl, shr. A decoder may therefore pass the
    // funct field through unchanged. This is a deliberate dependency on
    // tools/isa/isa.yaml, verified by tools/isa/check_names.py.
    typedef logic [3:0] AluOp;
    localparam AluOp ALU_ADD   = 4'd0;
    localparam AluOp ALU_XOR   = 4'd1;
    localparam AluOp ALU_SHL   = 4'd2;
    localparam AluOp ALU_SHR   = 4'd3;
    localparam AluOp ALU_CMP   = 4'd4;                      // unsigned three-way compare: 1 if a > b, all ones if a < b, 0 if equal
    localparam AluOp ALU_CMPA  = 4'd5;                      // signed three-way compare
    localparam AluOp ALU_AND   = 4'd6;
    localparam AluOp ALU_OR    = 4'd7;
    localparam AluOp ALU_PASSB = 4'd8;                      // result = b                  (lbi, first half of lli)
    localparam AluOp ALU_LUI   = 4'd9;                      // result = {b[7:0], a[23:0]}  (lui)

    // Jump kind.
    typedef logic [2:0] BrType;
    localparam BrType BR_NONE = 3'd0;
    localparam BrType BR_JMP  = 3'd1;                       // PC + 1 + offset, link in rd
    localparam BrType BR_JRG  = 3'd2;                       // rs1 + immediate, link in rd
    localparam BrType BR_JNL  = 3'd3;                       // PC + 1 + offset, no link
    localparam BrType BR_JOF  = 3'd4;                       // conditional on one flag
    localparam BrType BR_JOC  = 3'd5;                       // conditional on a flag mask

    // Memory operation.
    typedef logic [1:0] MemOp;
    localparam MemOp MEM_NONE  = 2'd0;
    localparam MemOp MEM_LOAD  = 2'd1;
    localparam MemOp MEM_STORE = 2'd2;

    // Condition mode shared by joc and waitev. The invert option is a separate signal.
    localparam logic COND_ANY = 1'b0;
    localparam logic COND_ALL = 1'b1;

    //--------------------------------------------------------------------------
    // [4] Stage B interfaces
    //     Names and values fixed in advance. Not referenced by Stage A logic.
    //--------------------------------------------------------------------------

    // Pins. Pin n belongs to thread (n mod 3) at reset.
    // The grouping below is provisional until confirmed against the template.
    localparam int NUM_PINS   = 24;
    localparam int PIN_UI_LO  = 0,  PIN_UI_HI  = 7;         // ui:  input only
    localparam int PIN_UO_LO  = 8,  PIN_UO_HI  = 15;        // uo:  output only, drives 0 while its source is off
    localparam int PIN_UIO_LO = 16, PIN_UIO_HI = 23;        // uio: bidirectional

    // Watcher modes. Encoding 011 is reserved; a cfg using it is a bad cfg.
    typedef logic [2:0] WatchMode;
    localparam WatchMode WATCH_OFF  = 3'd0;
    localparam WatchMode WATCH_LOW  = 3'd1;                 // live level
    localparam WatchMode WATCH_HIGH = 3'd2;                 // live level
    localparam WatchMode WATCH_OFF2 = 3'd4;                 // second encoding of OFF
    localparam WatchMode WATCH_POS  = 3'd5;                 // sticky, rising edge
    localparam WatchMode WATCH_NEG  = 3'd6;                 // sticky, falling edge
    localparam WatchMode WATCH_ANY  = 3'd7;                 // sticky, either edge

    // Pin output source.
    typedef logic [1:0] OutSrc;
    localparam OutSrc OSRC_OFF      = 2'd0;
    localparam OutSrc OSRC_DIRECT   = 2'd1;                 // driven by wpin
    localparam OutSrc OSRC_ENG_DATA = 2'd2;                 // shift engine data
    localparam OutSrc OSRC_ENG_CLK  = 2'd3;                 // shift engine clock

    // Pin ownership transfer code. Encoding 3 is reserved.
    typedef logic [1:0] OwnerCode;
    localparam OwnerCode OWN_KEEP = 2'd0;
    localparam OwnerCode OWN_NEXT = 2'd1;                   // thread (i + 1) mod 3
    localparam OwnerCode OWN_PREV = 2'd2;                   // thread (i - 1) mod 3

    // cfg #PIN value packing. Bits not listed are reserved and must be zero.
    localparam int PINCFG_PIN_HI   = 4,  PINCFG_PIN_LO   = 0;
    localparam int PINCFG_WATCH_HI = 7,  PINCFG_WATCH_LO = 5;
    localparam int PINCFG_OSRC_HI  = 9,  PINCFG_OSRC_LO  = 8;
    localparam int PINCFG_DATA_IN  = 10;
    localparam int PINCFG_CLK_IN   = 11;
    localparam int PINCFG_GATE     = 12;
    localparam int PINCFG_OD       = 13;
    localparam int PINCFG_IDLE     = 14;
    localparam int PINCFG_OWNER_HI = 16, PINCFG_OWNER_LO = 15;
    // cfg #WATCH value: [4:0] pin and [7:5] watcher mode, at the same positions as above.
    // cfg #ENG_DIV value: [15:0] divisor, nonzero.

    // cfg #ENG_CTL bit positions. Bits [4:3] are reserved for streaming and
    // line-coding extensions and are decoded as must-be-zero.
    localparam int ENGCTL_MSB_FIRST = 0;                    // 0: LSB first
    localparam int ENGCTL_DUPLEX    = 1;
    localparam int ENGCTL_CPHA      = 2;

    // Hardware loader. All values are provisional.
    localparam logic [15:0] LDR_CMD_WRITE_I = 16'hA55A;
    localparam logic [15:0] LDR_CMD_WRITE_D = 16'h5AA5;
    localparam logic [15:0] LDR_CMD_ENTRY0  = 16'hC33C;
    localparam logic [15:0] LDR_CMD_ENTRY1  = 16'h3CC3;
    localparam logic [15:0] LDR_CMD_ENTRY2  = 16'h9696;
    localparam logic [15:0] LDR_CMD_GO      = 16'h6969;
    localparam int LDR_PIN_CLK = 0, LDR_PIN_DATA = 1, LDR_PIN_EN = 2, LDR_PIN_ERR = 8;

    // Build-variant defaults. Top-level modules expose these as parameters so
    // that a build can override them without editing this package.
    localparam int SAMPLE_COMP_DEFAULT = 0;                 // 0 or 2: delay of engine sample strobes, in cycles
    localparam int PIN_INVERT_DEFAULT  = 0;                 // 1: per-pin output-invert stage
    localparam int ENG_GAPLESS_DEFAULT = 0;                 // 1: shadow ISR/OSR and continuous-run mode

endpackage