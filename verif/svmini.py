"""svmini: a small interpreter for the SystemVerilog subset used by mda_decoder.sv and mda_imm_gen.sv.
Supports: packages' localparams, assign, always_comb with begin/end, if/else, case/default, blocking assignment,
expressions with widths (concat, replication, part/bit select, ternary, shifts, comparisons, logic ops)."""
import re
TOK=re.compile(r"""\s*(?:(?P<num>\d+\s*'[sS]?[bBdDhHoO][0-9a-fA-FxXzZ_?]+|'[01]|\d+)|(?P<id>\$?[A-Za-z_]\w*(?:::\w+)?)|(?P<op><<<|>>>|<<|>>|<=|>=|==|!=|&&|\*\*|\|\||[-+*/%&|^~!?:(){}\[\],;=<>.@#]))""",re.X)
def preprocess(src):
    out=[]; stack=[]      # stack of 'keep' flags
    for line in src.split('\n'):
        t=line.strip()
        if t.startswith('`ifdef') or t.startswith('`ifndef'):
            stack.append(t.startswith('`ifndef'))          # ifdef of an undefined macro: skipped; ifndef: kept
        elif t.startswith('`else'):
            stack[-1]=not stack[-1]
        elif t.startswith('`endif'):
            stack.pop()
        elif all(stack): out.append(line)
    return '\n'.join(out)
def tokenize(src):
    src=preprocess(src)
    src=re.sub(r'/\*.*?\*/','',src,flags=re.S); src=re.sub(r'//[^\n\r]*','',src); src=re.sub(r'\(\*.*?\*\)','',src,flags=re.S)
    toks=[]; pos=0
    while pos<len(src):
        m=TOK.match(src,pos)
        if not m:
            if src[pos:].strip()=='': break
            raise SyntaxError("cannot tokenize: "+src[pos:pos+30])
        pos=m.end()
        for k in ('num','id','op'):
            if m.group(k) is not None: toks.append((k,m.group(k).replace(' ','')))
    return toks
def M(w): return (1<<w)-1
def parse_num(t):
    if t in ("'0","'1"): return ('num',0 if t=="'0" else -1,None)
    m=re.match(r"(\d+)'[sS]?([bBdDhHoO])([0-9a-fA-F_xXzZ?]+)$",t)
    if m:
        w=int(m.group(1)); base={'b':2,'d':10,'h':16,'o':8}[m.group(2).lower()]
        digits=m.group(3).replace('_','')
        if '?' in digits:                                   # casez wildcard bits (binary literals only)
            assert base==2
            val=int(digits.replace('?','0'),2); wild=int(''.join('1' if c=='?' else '0' for c in digits),2)
            return ('num',val&M(w),w,wild)
        return ('num',int(digits,base)&M(w),w)
    return ('num',int(t),32)
LEVELS=[['||'],['&&'],['|'],['^'],['&'],['==','!='],['<','<=','>','>='],['<<','>>','>>>'],['+','-'],['*','/','%'],['**']]
class Parser:
    def __init__(s,toks): s.t=toks; s.i=0
    def pk(s,k=0): return s.t[s.i+k][1] if s.i+k<len(s.t) else None
    def nx(s): v=s.t[s.i]; s.i+=1; return v
    def ex(s,v):
        assert s.pk()==v,f"expected {v!r} got {s.pk()!r} at token {s.i}: {[x[1] for x in s.t[s.i-4:s.i+4]]}"; s.i+=1
    # ---- expressions
    def expr(s):
        c=s.binary(0)
        if s.pk()=='?':
            s.nx(); a=s.expr(); s.ex(':'); b=s.expr(); return ('?',c,a,b)
        return c
    def binary(s,lv):
        if lv==len(LEVELS): return s.unary()
        a=s.binary(lv+1)
        while s.pk() in LEVELS[lv]:
            op=s.nx()[1]; b=s.binary(lv+1); a=('bin',op,a,b)
        return a
    def unary(s):
        if s.pk() in ('!','~','-'):
            op=s.nx()[1]; return ('un',op,s.unary())
        if s.pk() in ('&','|','^'):
            op=s.nx()[1]; return ('red',op,s.unary())
        return s.primary()
    def primary(s):
        k,v=s.t[s.i]
        if k=='num': s.i+=1; return parse_num(v)
        if v=='(':
            s.nx(); e=s.expr(); s.ex(')'); return e
        if v=='{':
            s.nx(); first=s.expr()
            if s.pk()=='{':
                s.nx(); parts=[s.expr()]
                while s.pk()==',': s.nx(); parts.append(s.expr())
                s.ex('}'); s.ex('}'); return ('rep',first,('cat',parts))
            parts=[first]
            while s.pk()==',': s.nx(); parts.append(s.expr())
            s.ex('}'); return ('cat',parts)
        if k=='id' and v.startswith('$'):
            s.i+=1; s.ex('('); args=[s.expr()]
            while s.pk()==',': s.nx(); args.append(s.expr())
            s.ex(')'); return ('call',v,args)
        if k=='id':
            s.i+=1; name=v.split('::')[-1]
            if s.pk()=='[':
                s.nx(); hi=s.expr()
                if s.pk()==':': s.nx(); lo=s.expr(); s.ex(']'); return ('sel',name,hi,lo)
                s.ex(']'); return ('sel',name,hi,None)
            return ('id',name)
        raise SyntaxError(f"bad primary {v!r}")
    # ---- statements
    def stmt(s):
        v=s.pk()
        if v=='begin':
            s.nx(); body=[]
            while s.pk()!='end': body.append(s.stmt())
            s.nx(); return ('block',body)
        if v=='if':
            s.nx(); s.ex('('); c=s.expr(); s.ex(')'); a=s.stmt(); b=None
            if s.pk()=='else': s.nx(); b=s.stmt()
            return ('if',c,a,b)
        if v in ('case','casez','casex'):
            s.nx(); s.ex('('); sel=s.expr(); s.ex(')'); items=[]; default=None
            while s.pk()!='endcase':
                if s.pk()=='default':
                    s.nx(); s.ex(':'); default=s.stmt()
                else:
                    labels=[s.expr()]
                    while s.pk()==',': s.nx(); labels.append(s.expr())
                    s.ex(':'); items.append((labels,s.stmt()))
            s.nx(); return ('case',sel,items,default)
        if v=='for':
            s.nx(); s.ex('(')
            while s.pk() in ('int','integer','logic','reg'): s.nx()
            var=s.nx()[1]; s.ex('='); init=s.expr(); s.ex(';'); cond=s.expr(); s.ex(';')
            var2=s.nx()[1]; s.ex('='); step=s.expr(); s.ex(')'); body=s.stmt()
            return ('for',var,init,cond,var2,step,body)
        if v=='{':
            s.nx(); names=[s.nx()[1]]
            while s.pk()==',': s.nx(); names.append(s.nx()[1])
            s.ex('}'); s.ex('='); e=s.expr(); s.ex(';'); return ('assign_cat',names,e)
        name=s.nx()[1]
        if s.pk()=='[':
            s.nx(); idx=s.expr(); s.ex(']')
            if s.pk()=='<=':
                s.nx(); e=s.expr(); s.ex(';'); return ('nba_idx',name,idx,e)
            s.ex('='); e=s.expr(); s.ex(';'); return ('assign_idx',name,idx,e)
        if s.pk()=='<=':
            s.nx(); e=s.expr(); s.ex(';'); return ('nba',name,e)
        s.ex('='); e=s.expr(); s.ex(';'); return ('assign',name,e)
def ev(n,env,cw=0):
    t=n[0]
    if t=='num': return (n[1],n[2])
    if t=='id': return env[n[1]]
    if t=='sel':
        v,w=env[n[1]]
        if isinstance(v,list): return (v[ev(n[2],env)[0]%len(v)],w)
        hi=ev(n[2],env)[0]
        lo=ev(n[3],env)[0] if n[3] is not None else hi
        return ((v>>lo)&M(hi-lo+1),hi-lo+1)
    if t=='un':
        v,w=ev(n[2],env,cw if n[1] in ('~','-') else 0)
        if n[1]=='!': return (0 if v else 1,1)
        if n[1]=='~': return ((~v)&M(w),w)
        return ((-v)&M(w),w)
    if t=='call':
        args=[ev(a,env) for a in n[2]]
        if n[1]=='$clog2':
            x=args[0][0]; return ((max(x-1,0)).bit_length(),32)
        if n[1]=='$signed':
            v,w=args[0]; return ((v-(1<<w) if (w and v>>(w-1)) else v),w)
        raise ValueError(n[1])
    if t=='red':
        v,w=ev(n[2],env)
        if n[1]=='&': return (1 if v==M(w) else 0,1)
        if n[1]=='|': return (1 if v else 0,1)
        return (bin(v).count('1')&1,1)
    if t=='bin':
        op=n[1]; arith=op in ('+','-','*','&','|','^','<<','>>','>>>','**'); sc=cw if arith else 0
        a,wa=ev(n[2],env,sc); b,wb=ev(n[3],env,0 if op in ('<<','>>','>>>','**') else sc)
        wa_=wa or 0; wb_=wb or 0; w=max(wa_,wb_,sc) or 32
        if op=='&&': return (1 if (a and b) else 0,1)
        if op=='||': return (1 if (a or b) else 0,1)
        if op=='==': return (1 if a==b else 0,1)
        if op=='!=': return (1 if a!=b else 0,1)
        if op=='<': return (1 if a<b else 0,1)
        if op=='<=': return (1 if a<=b else 0,1)
        if op=='>': return (1 if a>b else 0,1)
        if op=='>=': return (1 if a>=b else 0,1)
        if op=='<<': return ((a<<b)&M(max(wa_,sc) or 32),max(wa_,sc) or 32)
        if op in('>>','>>>'): return ((a>>b),max(wa_,sc) or 32)
        if op=='+': return ((a+b)&M(w),w)
        if op=='-': return ((a-b)&M(w),w)
        if op=='*': return ((a*b)&M(w),w)
        if op=='**': return ((a**b)&M(w),w)
        if op=='&': return (a&b,w)
        if op=='|': return (a|b,w)
        if op=='^': return (a^b,w)
        raise ValueError(op)
    if t=='?':
        c,_=ev(n[1],env); a=ev(n[2],env,cw); b=ev(n[3],env,cw)
        r=a if c else b; return r
    if t=='cat':
        val=0; tot=0
        for p in n[1]:
            v,w=ev(p,env); assert w is not None,"unsized value in concatenation"
            val=(val<<w)|(v&M(w)); tot+=w
        return (val,tot)
    if t=='rep':
        cnt=ev(n[1],env)[0]; v,w=ev(n[2],env); val=0
        for _ in range(cnt): val=(val<<w)|v
        return (val,cnt*w)
    raise ValueError(t)
NBA=[]
def set_idx(env,name,idx,val,w_unused=None):
    cur,w=env[name]
    if isinstance(cur,list): cur[idx%len(cur)]=val&M(w)
    else: env[name]=((cur&~(1<<idx))|((val&1)<<idx),w)
def apply_nba(env,lst):
    for rec in lst:
        if rec[0]=='idx': set_idx(env,rec[1],rec[2],rec[3])
        else: env[rec[1]]=(rec[2],rec[3])
def exe(n,env,widths):
    t=n[0]
    if t=='nba':
        tw=widths.get(n[1]); v,w=ev(n[2],env,tw or 0); NBA.append(('set',n[1],(v&M(tw)) if tw else v,tw if tw else w)); return
    if t=='nba_idx':
        NBA.append(('idx',n[1],ev(n[2],env)[0],ev(n[3],env)[0])); return
    if t=='assign_idx':
        set_idx(env,n[1],ev(n[2],env)[0],ev(n[3],env)[0]); return
    if t=='assign_cat':
        names=n[1]; ws=[widths[x] for x in names]; shift=sum(ws); v,w=ev(n[2],env,shift)
        for x,wx in zip(names,ws):
            shift-=wx; env[x]=((v>>shift)&M(wx),wx)
        return
    if t=='for':
        _,var,init,cond,var2,step,body=n; env[var]=(ev(init,env)[0],32); it=0
        while ev(cond,env)[0] and it<1000:
            exe(body,env,widths); env[var2]=(ev(step,env)[0],32); it+=1
        return
    if t=='block':
        for x in n[1]: exe(x,env,widths)
    elif t=='assign':
        tw=widths.get(n[1]); v,w=ev(n[2],env,tw or 0)
        if w is None: v=0 if v==0 else M(tw)
        if tw is not None: v&=M(tw)
        env[n[1]]=(v,tw if tw is not None else w)
    elif t=='if':
        c,_=ev(n[1],env)
        if c: exe(n[2],env,widths)
        elif n[3] is not None: exe(n[3],env,widths)
    elif t=='case':
        sel,_=ev(n[1],env)
        for labels,body in n[2]:
            if any((((ev(l,env)[0]^sel)&~(l[3] if (l[0]=='num' and len(l)>3) else 0))==0) for l in labels): exe(body,env,widths); return
        if n[3] is not None: exe(n[3],env,widths)
def package_consts(*paths):
    env={}
    for p in paths:
        toks=tokenize(open(p).read()); i=0
        while i<len(toks):
            if toks[i][1]=='localparam':
                i+=1; names=[]
                # tokens up to '=' : the last identifier is the name
                while True:
                    j=i
                    while toks[j][1]!='=': j+=1
                    name=toks[j-1][1]
                    pr=Parser(toks); pr.i=j+1; e=pr.expr()
                    v,w=ev(e,env); env[name]=(v,w if w is not None else 32)
                    i=pr.i
                    if toks[i][1]==',': i+=1; continue
                    break
            else: i+=1
    return env
class Module:
    def __init__(s,path,consts,widths):
        toks=tokenize(open(path).read()); s.consts=consts; s.widths=widths; i=0
        while toks[i][1]!='module': i+=1
        i+=2
        def skip_paren(i):
            assert toks[i][1]=='('; d=0
            while True:
                if toks[i][1]=='(': d+=1
                if toks[i][1]==')':
                    d-=1
                    if d==0: return i+1
                i+=1
        if toks[i][1]=='#': i=skip_paren(i+1)
        i=skip_paren(i); assert toks[i][1]==';'; i+=1
        s.items=[]; pr=Parser(toks); pr.i=i
        while pr.pk()!='endmodule':
            v=pr.pk()
            if v=='assign':
                pr.nx(); name=pr.nx()[1]; pr.ex('='); e=pr.expr(); pr.ex(';'); s.items.append(('assign',name,e))
            elif v=='always_comb':
                pr.nx(); s.items.append(pr.stmt())
            elif v=='always_ff':
                pr.nx(); pr.ex('@'); d=0
                while True:
                    if pr.pk()=='(': d+=1
                    if pr.pk()==')':
                        d-=1
                        if d==0: pr.nx(); break
                    pr.nx()
                s.items.append(('ff',pr.stmt()))
            elif pr.t[pr.i][0]=='id' and pr.i+2<len(pr.t) and pr.t[pr.i+1][0]=='id' and pr.t[pr.i+2][1]=='(':
                mod=pr.nx()[1]; inst=pr.nx()[1]; pr.ex('('); conns={}
                while pr.pk()!=')':
                    pr.ex('.'); port=pr.nx()[1]; pr.ex('('); e=pr.expr(); pr.ex(')'); conns[port]=e
                    if pr.pk()==',': pr.nx()
                pr.ex(')'); pr.ex(';'); s.items.append(('inst',mod,inst,conns))
            else:
                while pr.pk()!=';': pr.nx()
                pr.nx()
    def run(s,inputs):
        env=dict(s.consts)
        for k,v in inputs.items(): env[k]=(v&M(s.widths[k]),s.widths[k])
        for _ in range(4):
            for it in s.items:
                if it[0]=='inst':
                    sub,ins,outs=s.lib[it[1]]
                    o=sub.run({p:ev(it[3][p],env)[0] for p in ins})
                    for p in outs: env[it[3][p][1]]=(o[p],s.widths.get(it[3][p][1]))
                elif it[0]!='ff': exe(it,env,s.widths)
        return {k:env[k][0] for k in s.widths if k in env}
    lib={}
    def init_state(s,rng=None):
        import random
        rng=rng or random.Random(0); s.st=dict(s.consts)
        for k,w in s.widths.items(): s.st[k]=(rng.getrandbits(w),w)       # unreset flops start random
    def peek(s,inputs):
        env=dict(s.st)
        for k,v in inputs.items(): env[k]=(v&M(s.widths[k]),s.widths[k])
        for _ in range(4):
            for it in s.items:
                if it[0]=='inst': continue
                if it[0]!='ff': exe(it,env,s.widths)
        return {k:env[k][0] for k in s.widths if k in env}
    def step(s,inputs,rst_n=1):
        env=s.st
        for k,v in inputs.items(): env[k]=(v&M(s.widths[k]),s.widths[k])
        env['rst_n']=(rst_n,1)
        for it in s.items:
            if it[0]!='ff': exe(it,env,s.widths)
        del NBA[:]
        for it in s.items:
            if it[0]=='ff': exe(it[1],env,s.widths)
        apply_nba(env,NBA)
        for it in s.items:
            if it[0]!='ff': exe(it,env,s.widths)
        return {k:env[k][0] for k in s.widths if k in env}
