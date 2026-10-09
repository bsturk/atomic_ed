; Bounded scenario terrain constants. No changes to calcMC's cost algorithm,
; fortification/supply/fatigue arithmetic, or the native combat resolution.
%define TERRAIN_WORDS 414
%define TERRAIN_BYTES 844

read_terrain_rules: ; cdecl(fd), stage only; commit after the REZ/AI open succeeds
    enter_fn 0
    push byte 2
    push dword -64-TERRAIN_BYTES
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    test eax, eax
    js .bad
    push dword TERRAIN_BYTES
    lea eax, [ebx+staged_terrain]
    push eax
    push dword [ebp+0x14]
    call READ
    add esp, 12
    cmp eax, TERRAIN_BYTES
    jne .bad
    lea esi, [ebx+staged_terrain]
    cmp dword [esi], 'WAWT'
    jne .bad
    cmp dword [esi+4], 'ER01'
    jne .bad
    cmp dword [esi+8], TERRAIN_BYTES
    jne .bad
    xor ecx, ecx
    xor edi, edi
.check:
    movzx eax, word [esi+16+ecx*2]
    add edi, eax
    cmp ecx, 336
    jae .road
    cmp eax, 500
    ja .bad
    push eax
    mov eax, ecx
    xor edx, edx
    push byte 14
    pop ebx
    div ebx
    cmp edx, 5
    je .blocked
    cmp eax, 10
    je .blocked
    cmp eax, 22
    je .blocked
    pop eax
    jmp .next
.blocked:
    pop eax
    test eax, eax
    jnz .bad
    jmp .next
.road:
    cmp ecx, 372
    jae .combat
    cmp eax, 5000
    ja .bad
    cmp ecx, 366
    jb .mobile
    cmp ecx, 369
    jae .mobile
    test eax, eax
    jnz .bad
    jmp .next
.mobile:
    test eax, eax
    jz .bad
    jmp .next
.combat:
    cmp eax, 400
    ja .bad
.next:
    inc ecx
    cmp ecx, TERRAIN_WORDS
    jb .check
    cmp edi, [esi+12]
    jne .bad
    mov eax, 1
    leave_fn
.bad:
    xor eax, eax
    leave_fn

commit_terrain_rules: ; caller's EBX/EDI = code/data bases
    pushad
    lea esi, [ebx+default_roads]
    test dword [ebx+active+48], 4
    jz .roads
    push edi
    lea esi, [ebx+staged_terrain+16]
    lea edi, [ebx+terrain_rules]
    mov ecx, TERRAIN_WORDS/2
    rep movsd
    pop edi
    lea esi, [ebx+terrain_rules+672]
.roads:
    push edi
    add edi, 0x824c
    mov ecx, 18
    rep movsd
    pop edi
    ; AI positioning uses heuristic weights, sometimes different from actual
    ; combat multipliers. Preserve each stock heuristic unless its associated
    ; combat value changed. Movement/AI both read the same live road table.
    xor ecx, ecx
.ai:
    movzx eax, word [ebx+default_ai+ecx*2]
    test dword [ebx+active+48], 4
    jz .ai_store
    movzx edx, word [ebx+terrain_rules+744+ecx*2]
    cmp dx, [ebx+default_combat+ecx*2]
    je .ai_store
    mov eax, edx
.ai_store:
    mov edx, ecx
    cmp ecx, 14
    jb .defense
    cmp ecx, 28
    jb .armor
    sub edx, 28
    mov [edi+0x83fa+edx*2], ax
    jmp .ai_next
.armor:
    sub edx, 14
    mov [edi+0x844e+edx*2], ax
    jmp .ai_next
.defense:
    mov [edi+0x8424+edx*2], ax
.ai_next:
    inc ecx
    cmp ecx, 42
    jb .ai
    popad
    ret

terrain_base_cost: ; cdecl(x,y,mobility,side), result AX in thousandths
    enter_fn 0
    test dword [ebx+active+48], 4
    jz .native
    push dword [ebp+0x18]
    push dword [ebp+0x14]
    call 0x4a289 ; TERRAIN
    add esp, 8
    movzx ecx, al
    cmp ecx, 14
    jae .native ; special graphics retain native behavior
    movzx edx, byte [ebp+0x1c]
    cmp edx, 12
    jae .blocked
    imul edx, 14
    add ecx, edx
    mov eax, [edi+0x7d67]
    movzx eax, byte [eax+0x4bc] ; dry/light mud, engine patch v4 offset
    cmp eax, 1
    ja .native ; later ground states have no verified D-Day cost table
    test eax, eax
    jz .cost
    add ecx, 168
.cost:
    movzx eax, word [ebx+terrain_rules+ecx*2]
    imul eax, 10
    leave_fn
.blocked:
    xor eax, eax
    leave_fn
.native:
    mov esp, ebp
    pop ebp
    pop edi
    pop esi
    pop ebx
    push ebx
    push esi
    push edi
    push ebp
    mov ebp, esp
    jmp 0x2ba87

; Mid-function hooks preserve the original frame and all registers. Defaults
; execute the original arithmetic, including its native integer rounding.
terrain_defense:
    pushad
    call bases
    test dword [ebx+active+48], 4
    jz .native
    movzx esi, word [ebp-4]
    cmp esi, 14
    jae .native
    movzx ecx, word [ebx+terrain_rules+744+esi*2]
    cmp cx, [ebx+default_combat+esi*2]
    jne .custom
    movzx ecx, word [ebx+terrain_rules+772+esi*2]
    cmp cx, [ebx+default_combat+28+esi*2]
    je .native
.custom:
    mov edi, [ebp+0x14]
    mov eax, [edi+0x24]
    movzx ecx, word [ebx+terrain_rules+744+esi*2]
    call terrain_percent
    mov [edi+0x24], eax
    mov eax, [edi+0x34]
    movzx ecx, word [ebx+terrain_rules+772+esi*2]
    call terrain_percent
    mov [edi+0x34], eax
    popad
    jmp 0x14f2f
.native:
    popad
    mov eax, [ebp-4]
    mov [ebp-0x2c], eax
    jmp 0x14e9c

terrain_barrage:
    pushad
    call bases
    test dword [ebx+active+48], 4
    jz .native
    movzx esi, word [ebp-0x18]
    cmp esi, 14
    jae .native
    movzx ecx, word [ebx+terrain_rules+800+esi*2]
    cmp cx, [ebx+default_combat+56+esi*2]
    je .native
    mov eax, [ebp+0x14]
    call terrain_percent
    mov [ebp+0x14], eax
    popad
    jmp 0xd734
.native:
    popad
    cmp word [ebp-0x18], 13
    jmp 0xd6a0

terrain_percent: ; signed strength * unsigned percentage /100, truncate;
    imul ecx     ; saturate extreme authored strengths instead of IDIV overflow
    cmp edx, 49
    jg .maximum
    jl .minimum_test
    cmp eax, 0xffffff9c
    ja .maximum
.minimum_test:
    cmp edx, -50
    jl .minimum
    mov ecx, 100
    idiv ecx
    ret
.maximum:
    mov eax, 0x7fffffff
    ret
.minimum:
    mov eax, 0x80000000
    ret

align 4
default_roads:
    dw 375,250,375, 325,250,250, 325,250,250, 325,250,250
    dw 325,150,250, 325,125,250, 325,125,250, 325,125,250
    dw 325,165,250, 325,125,250, 0,0,0, 375,250,375
default_combat:
    dw 100,100,100,100,100,100,100,150,150,200,100,100,100,100
    dw 200,100,150,150,150,100,100,200,200,300,200,250,100,100
    dw 75,100,80,80,80,100,100,50,50,25,50,50,100,100
default_ai:
    dw 100,100,100,100,100,100,100,100,100,100,250,250,100,100
    dw 200,100,150,100,150,100,100,200,200,100,200,200,100,200
    dw 50,100,50,80,80,100,50,75,50,50,25,25,100,50
terrain_rules: times TERRAIN_WORDS dw 0
staged_terrain: times TERRAIN_BYTES db 0
