import sys, random, time
import os
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.environ.get('MDA_ROOT') or os.path.abspath(os.path.join(HERE,'..'))   # verif/ sits directly under the repo root
sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(ROOT,'tools','isa'))
from svmini import *
from isa_gen import Isa
isa=Isa(os.path.join(ROOT,'tools','isa','isa.yaml'))
PK=os.path.join(ROOT,'src','mda_pkg.sv'); IP=os.path.join(ROOT,'src','mda_isa_pkg.sv')
DEC_W=dict(instr=16,suffix_pend=1,suffix_rd=3,rs1_addr=3,rs2_addr=3,rd_addr=3,reg_write=1,alu_op=3,use_imm=1,fwd_imm=1,res_sel=2,imm_sel=4,
           f_u_alu=1,illegal=1,br_type=3,br_jof_inv=1,br_joc_all=1,mem_op=2,mem_byte=1,lli_first=1,sp_valid=1,sp_op=4,
           opcode=3,funct3=3,funct2=2,wb=1,wb_ria=1,ill=1,is_lui=1)
IMM_W=dict(instr=16,imm_sel=4,rs1_data=32,suffix_imm8=8,imm_out=32)
OUT=['rs1_addr','rs2_addr','rd_addr','reg_write','alu_op','use_imm','fwd_imm','res_sel','imm_sel','f_u_alu','illegal','br_type','br_jof_inv','br_joc_all','mem_op','mem_byte','lli_first','sp_valid','sp_op']
ALUC={'add':0,'xor':1,'shl':2,'shr':3,'cmp':4,'cmpa':5,'and':6,'or':7}
IMMNAME={'addi':'S4','xori':'S4','shli':'U4','shri':'U4','lb':'MEM_B','lw':'MEM_W','sb':'ST_B','sw':'ST_W','lbi':'LBI','lui':'LUI'}   # jumps use IMM_NONE
SPN={'pull':'PULL','push':'PUSH','inp':'INP','outp':'OUTP','rpin':'RPIN','wpin':'WPIN','dl':'DL','dlrg':'DLRG','waitev':'WAITEV','cfg':'CFG','flg':'FLG'}
def expected(word,sp,srd,C):
    k=lambda n:C[n][0]
    ex={}
    isl = ((word&7)==6 and ((word>>3)&3)==0)
    ex['rs2_addr']=(word>>7)&7
    ex['rd_addr']=srd if sp else (word>>13)&7
    ex['rs1_addr']=(word>>13)&7 if isl else (word>>10)&7
    if sp:
        ex.update(alu_op=0,reg_write=1,use_imm=1,fwd_imm=1,res_sel=k('RES_ALU'),imm_sel=k('IMM_SUFFIX'),f_u_alu=0,illegal=0,br_type=k('BR_NONE'),
                  br_jof_inv=0,br_joc_all=0,mem_op=k('MEM_NONE'),mem_byte=0,lli_first=0,sp_valid=0,sp_op=k('SP_NONE'))
        return ex,{'rs1_addr'}                      # rs1_addr is a don't-care in a suffix slot
    d=isa.decode(word)
    if not d['legal']:
        ex.update(illegal=1,reg_write=0,f_u_alu=0,mem_op=k('MEM_NONE'),br_type=k('BR_NONE'),lli_first=0,sp_valid=0,sp_op=k('SP_NONE'))
        return ex,set()
    n=d['name']; ins=isa.by_name[n]; s=ins.spec; alu=s.get('alu'); mem=s.get('mem'); br=s.get('branch')
    is_alu=alu in ALUC
    if s.get('dst')=='rd':
        if (mem and mem['op']=='load') or n=='lli': rw=0
        elif s.get('dst_when')=='wb': rw=d['wb']
        else: rw=1
    else: rw=0
    ex.update(illegal=0,reg_write=rw,alu_op=ALUC[alu] if is_alu else 0,use_imm=(1 if s.get('b_src')=='imm' else 0) if is_alu else 1,
              fwd_imm=0 if (is_alu or mem) else 1,
              res_sel=k('RES_LINK') if (br and s.get('link')) else (k('RES_SP') if (ins.stage=='B' and s.get('dst')=='rd') else k('RES_ALU')),
              imm_sel=k('IMM_'+IMMNAME[n]) if n in IMMNAME else k('IMM_NONE'),
              f_u_alu=1 if 'Z' in s.get('flags',[]) else 0,
              br_type=k('BR_'+br['kind'].upper()) if br else k('BR_NONE'),
              br_jof_inv=1 if n=='jof_inv' else 0, br_joc_all=1 if n=='joc_all' else 0,
              mem_op=k('MEM_'+mem['op'].upper()) if mem else k('MEM_NONE'), mem_byte=(1 if mem['size']=='byte' else 0) if mem else 0,
              lli_first=1 if n=='lli' else 0, sp_valid=1 if (ins.stage=='B') else 0,
              sp_op=k('SP_'+SPN[n]) if (ins.stage=='B') else k('SP_NONE'))
    return ex,set()
def expected_imm(word,sel_name,rs1,sfx8,d):
    f=d['fields'] if d and d.get('legal') else {}
    n=d['name'] if d and d.get('legal') else None
    M32=(1<<32)-1
    if sel_name=='SUFFIX': return ((sfx8<<16)|word)&M32
    if n in ('addi','xori','shli','shri'):
        return f['imm']&M32                          # jumps are not here any more: their immediate is IMM_NONE (0)
    if n in('lb','sb'): return f['offset']&M32
    if n in('lw','sw'): return (f['offset']*4)&M32
    if n=='lbi': return f['imm']
    if n=='lui': return ((f['imm']<<24)|(rs1&0xFFFFFF))&M32
    return 0
def branch_offset_ref(word,isa=isa):
    """Reference for the PC offset that mda_branch_unit must produce (pc_offset, 10 bits, two's complement) for a legal jump word."""
    d=isa.decode(word)
    if not d['legal'] or d['name'] not in ('jmp','jnl','jof','jof_inv','joc_any','joc_all','jrg'): return None
    return d['fields'].get('offset',d['fields'].get('imm')) & 0x3FF
def run_all(dec_path=None,imm_path=None,quiet=False,sample=None):
    C=package_consts(PK,IP)
    dec=Module(dec_path or os.path.join(ROOT,'src','mda_decoder.sv'),C,DEC_W)
    imm=Module(imm_path or os.path.join(ROOT,'src','mda_imm_gen.sv'),C,IMM_W)
    rng=random.Random(11); errs={}; n=0; nimm=0; imm_errs=0
    words=range(1<<16) if sample is None else rng.sample(range(1<<16),sample)
    for w in words:
        for sp in (0,1):
            srd=rng.randrange(8); o=dec.run(dict(instr=w,suffix_pend=sp,suffix_rd=srd)); n+=1
            ex,skip=expected(w,sp,srd,C)
            for key,val in ex.items():
                if key in skip: continue
                if o[key]!=val: errs.setdefault(key,[]).append((hex(w),sp,o[key],val))
            # immediate generator driven by the decoder's imm_sel (chain test)
            if sp==1 or isa.decode(w)['legal']:
                sel=o['imm_sel']; rs1=rng.getrandbits(32); sfx=rng.randrange(256)
                got=imm.run(dict(instr=w,imm_sel=sel,rs1_data=rs1,suffix_imm8=sfx))['imm_out']
                if sp==1: want=((sfx<<16)|w)&0xFFFFFFFF
                else:
                    d=isa.decode(w); want=expected_imm(w,None,rs1,sfx,d)
                nimm+=1
                if got!=want: imm_errs+=1; errs.setdefault('imm_out',[]).append((hex(w),sp,hex(got),hex(want)))
    return n,nimm,errs
if __name__=='__main__':
    t=time.time(); n,nimm,errs=run_all()
    print(f"decoder: {n} (word, suffix_pend) cases | imm_gen chain: {nimm} cases | elapsed {time.time()-t:.0f}s")
    if not errs: print("ALL OUTPUTS MATCH the spec-derived expectations")
    for k,v in errs.items(): print(f"  MISMATCH {k}: {len(v)} cases, e.g. {v[:2]}")
