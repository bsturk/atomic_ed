; Per-scenario rule tables, carried in the final 64 bytes of the matching REZ.
; No absolute addresses or new loader fixups. Old exports restore D-Day values.
read_game_rules: ; cdecl(fd), caller has already chosen a profile-required SCN
    enter_fn 4
    push byte 2
    push byte -64
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    test eax, eax
    js .bad
    push byte 64
    lea eax, [ebx+staged_rules]
    push eax
    push dword [ebp+0x14]
    call READ
    add esp, 12
    cmp eax, 64
    jne .bad
    lea esi, [ebx+staged_rules]
    cmp dword [esi], 'WAWP'
    jne .bad
    cmp dword [esi+4], 'RO01'
    jne .bad
    cmp dword [esi+60], 'RUL1'
    jne .bad
    xor edx, edx
    xor ecx, ecx
.check:
    mov eax, [esi+ecx*4+8]
    cmp eax, [ebx+rule_min+ecx*4]
    jb .bad
    cmp eax, [ebx+rule_max+ecx*4]
    ja .bad
    add edx, eax
    inc ecx
    cmp ecx, 12
    jb .check
    cmp edx, [esi+56]
    jne .bad
    mov eax, [esi+12]
    cmp eax, [esi+16]
    jbe .bad
    mov eax, 1
    leave_fn
.bad:
    xor eax, eax
    leave_fn

commit_game_rules:
    push esi
    push edi
    lea esi, [ebx+default_rules]
    test dword [ebx+active+48], 2
    jz .copy
    lea esi, [ebx+staged_rules+8]
.copy:
    lea edi, [ebx+game_rules]
    mov ecx, 12
    rep movsd
    pop edi
    pop esi
    ret

profile_victory: ; native GetVicLevel(winning_side*, level*)
    enter_fn 8
    mov esi, [edi+0x7d57]
    mov eax, [esi]
    mov edx, [esi+0x220]
    xor ecx, ecx
    cmp eax, edx
    jge .winner
    xchg eax, edx
    inc ecx
.winner:
    mov esi, [ebp+0x14]
    mov [esi], cl
    test edx, edx
    jg .scores
    mov edx, 100
    test eax, eax
    mov eax, 100
    jz .scores
    mov eax, 200
.scores:
    mov [ebp-4], edx
    mov ecx, 100
    imul ecx
    mov esi, eax
    mov edi, edx
    mov eax, [ebp-4]
    imul dword [ebx+game_rules+4]
    cmp edi, edx
    jg .major
    jl .minor_test
    cmp esi, eax
    jae .major
.minor_test:
    mov eax, [ebp-4]
    imul dword [ebx+game_rules+8]
    cmp edi, edx
    jg .minor
    jl .draw
    cmp esi, eax
    ja .minor
.draw:
    xor eax, eax
    jmp .store
.minor:
    mov eax, 1
    jmp .store
.major:
    mov eax, 2
.store:
    mov esi, [ebp+0x18]
    mov [esi], al
    leave_fn

profile_ground: ; native CalcSnowIceWetness(code,temp,snow*,ice*,wet*)
    enter_fn 28
    ; locals: snow delta, wet delta, factor, temperature, ice delta, scratch, old ice
    xor eax, eax
    mov [ebp-4], eax
    mov [ebp-8], eax
    mov dword [ebp-12], 1
    cmp dword [ebx+game_rules], 2
    jae .temperature
    mov eax, [edi+0x7d5f]
    cmp byte [eax+0x122b], 3
    jne .temperature
    inc dword [ebp-12]
.temperature:
    movsx eax, word [ebp+0x18]
    mov [ebp-16], eax
    movzx ecx, byte [ebp+0x14]
    cmp eax, 32
    jg .warm
    cmp ecx, 3
    je .light_snow
    cmp ecx, 4
    jne .ice
    mov eax, [ebx+game_rules+16]
    jmp .snow
.light_snow:
    mov eax, [ebx+game_rules+12]
.snow:
    mov [ebp-4], eax
    jmp .ice
.warm:
    sub eax, 32
    cdq
    mov esi, 10
    idiv esi
    neg eax
    sub eax, ecx
    cmp dword [ebx+game_rules], 0
    je .dry
    add eax, 4
    neg eax
.dry:
    imul eax, [ebx+game_rules+32]
    cmp ecx, 3
    jne .heavy_rain
    mov eax, [ebx+game_rules+20]
    jmp .wet
.heavy_rain:
    cmp ecx, 4
    jne .wet
    mov eax, [ebx+game_rules+24]
.wet:
    mov [ebp-8], eax
    cmp dword [ebp-16], 35
    jle .ice
    mov esi, [ebp+0x1c]
    cmp dword [esi], 0
    jle .ice
    mov eax, 35
    sub eax, [ebp-16]
    imul eax, [ebx+game_rules+28]
    mov [ebp-4], eax
    cmp dword [ebx+game_rules], 0
    jne .ice
    cdq
    mov ecx, 10
    idiv ecx
    sub [ebp-8], eax
.ice:
    cmp dword [ebx+game_rules], 0
    je .apply
    mov esi, [ebp+0x20]
    mov eax, [esi]
    mov [ebp-28], eax
    mov eax, 32
    sub eax, [ebp-16]
    mov [ebp-24], eax
    fild dword [ebp-24]
    fimul dword [ebx+million]
    fild dword [esi]
    fiadd dword [ebx+thousand]
    fimul dword [ebx+game_rules+36]
    fdivp st1, st0
    fistp dword [ebp-20]
    mov eax, [esi]
    mov edx, eax
    add edx, [ebp-20]
    mov ecx, [ebx+game_rules+40]
    cmp eax, ecx
    jl .freeze
    cmp edx, ecx
    jge .ice_add
    cmp dword [ebx+game_rules], 3
    jne .thaw
    mov dword [ebp-20], 0
    jmp .ice_add
.thaw:
    sub eax, [ebx+game_rules+44]
    jmp .ice_add
.freeze:
    cmp edx, ecx
    jl .ice_add
    add eax, [ebx+game_rules+44]
.ice_add:
    mov edx, [ebp-20]
    imul edx, [ebp-12]
    add eax, edx
    jns .ice_store
    xor eax, eax
.ice_store:
    mov [esi], eax
.apply:
    mov esi, [ebp+0x1c]
    mov eax, [ebp-4]
    imul eax, [ebp-12]
    add eax, [esi]
    jns .snow_store
    xor eax, eax
.snow_store:
    mov [esi], eax
    mov esi, [ebp+0x24]
    mov eax, [ebp-8]
    imul eax, [ebp-12]
    add eax, [esi]
    jns .wet_store
    xor eax, eax
.wet_store:
    mov [esi], eax
    ; Native D-Day also clamps an initially negative ice value.
    mov esi, [ebp+0x20]
    cmp dword [esi], 0
    jge .done
    mov dword [esi], 0
.done:
    leave_fn

align 4
million: dd 1000000
thousand: dd 1000
rule_min: dd 0,101,100,0,0,0,0,0,0,1,1000,0
rule_max: dd 3,10000,9999,10000,10000,10000,10000,10000,10000,1000,1000000,10000
default_rules: dd 0,200,125,10,40,15,45,8,5,18,12000,200
game_rules: dd 0,200,125,10,40,15,45,8,5,18,12000,200
staged_rules: times 64 db 0
