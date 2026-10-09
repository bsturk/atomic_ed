; Optional SELECT.BAT startup request. Only match a discovered DOS basename:
; the text is never used as a filesystem path. Return index, -1 if absent,
; or -2 for malformed/unavailable requests. An explicit failure must not
; silently start Bradley or another battle.
startup_selection:
    enter_fn 32                 ; name[16], fd, saved volume, result
    mov dword [ebp-28], -1
    lea eax, [ebp-24]
    call home_volume
    push 0x200
    lea eax, [ebx+startup_filename]
    push eax
    call OPEN
    add esp, 8
    test eax, eax
    js .restore
    mov [ebp-20], eax
    mov dword [ebp-28], -2
    push byte 16
    lea eax, [ebp-16]
    push eax
    push dword [ebp-20]
    call READ
    add esp, 12
    mov esi, eax
    push dword [ebp-20]
    call CLOSE
    add esp, 4
    cmp esi, 5
    jl .restore
    cmp esi, 14                ; 8.3 basename plus CRLF
    ja .restore
    lea edx, [ebp-16]
    cmp byte [edx+esi-1], 10
    jne .length
    dec esi
    cmp byte [edx+esi-1], 13
    jne .length
    dec esi
.length:
    cmp esi, 5
    jb .restore
    cmp esi, 12
    ja .restore
    mov byte [edx+esi], 0
    xor ecx, ecx
.characters:
    cmp byte [edx+ecx], 33      ; reject embedded NUL/control/space bytes
    jb .restore
    cmp byte [edx+ecx], 126
    ja .restore
    inc ecx
    cmp ecx, esi
    jb .characters
    xor esi, esi
.find:
    cmp esi, [ebx+state_count]
    jae .restore
    lea eax, [ebp-16]
    push eax
    mov eax, esi
    shl eax, 6
    lea eax, [ebx+records+eax+8]
    push eax
    call 0x8cc22              ; native case-insensitive comparison
    add esp, 8
    test eax, eax
    jz .found
    inc esi
    jmp .find
.found:
    mov [ebp-28], esi
.restore:
    movsx eax, word [ebp-24]
    push eax
    push byte 0
    call 0x86e4d
    add esp, 8
    mov eax, [ebp-28]
    leave_fn

startup_filename: db 'WAWSTART.TXT',0
startup_error_text: db 'Cannot select the requested battle. Run SELECT again with matching SCN/REZ/AI files.',0
