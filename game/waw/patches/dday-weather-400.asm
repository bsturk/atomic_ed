; D-Day (Watcom LE) weather extension. NASM -f bin.
; The existing code object's final page has 1120 bytes after virtual size B2BA0.
; Relative CALLs stay in object 1. Global addresses are read from instructions
; already relocated by the LE loader, so the cave needs no new LE fixups.
BITS 32
ORG 0xb2ba0

%define NEW_SIZE 0x4c6
%define CLOUDS 0x32c
%define FLAGS 0x4bc
%define START 0x4be
%define END 0x4c2
%define READ_LONG 0x2732b
%define WRITE_LONG 0x27381
%define READ_FILE 0x271a2
%define WRITE_FILE 0x27215
%define NEW_PTR 0x25014
%define DISPOSE_PTR 0x24fd2
%define DEBUG_STR 0x24d73
%define EXIT_SHELL 0x86288

; Export directory used by the patch builder (code-object-relative addresses).
dd rw_weather, set_dates, validate_weather, swap_weather, authored_ai

%macro enter 1-2 1
    push ebx
    push esi
    push edi
    push ebp
    mov ebp, esp
%if %1
    sub esp, %1
%endif
%if %2
    call code_base
%endif
%endmacro

code_base:
    call .pc
.pc:
    pop ebx
    sub ebx, .pc             ; code-object base; no new LE fixups
    ret
%macro leave_fn 0
    mov esp, ebp
    pop ebp
    pop edi
    pop esi
    pop ebx
    ret
%endmacro
%macro weather_cell 1
    mov %1, [cs:ebx + 0x27e82] ; relocated operand: PUSH DWORD [Weather]
%endmacro

rw_weather:
    enter 0
    weather_cell edi
    movsx esi, word [ebp + 0x14]
    cmp word [ebp + 0x18], 0
    jne .write
    push edi
    push esi
    call read_weather
    add esp, 8
    jmp .done
.write:
    push esi
    push NEW_SIZE
    call WRITE_LONG
    add esp, 8
    push NEW_SIZE
    push esi
    push dword [edi]
    call WRITE_FILE
    add esp, 12
.done:
    leave_fn

; cdecl read_weather(file, pointer-to-pointer), original or extended on disk.
read_weather:
    enter 4, 0              ; caller has already established EBX
    push dword [ebp + 0x14]
    call READ_LONG
    add esp, 4
    mov [ebp - 4], eax
    cmp eax, 794
    je .size_ok
    cmp eax, NEW_SIZE
    jne bad_weather
.size_ok:
    push NEW_SIZE
    push dword [ebp + 0x18]
    call NEW_PTR
    add esp, 8
    mov edi, [ebp + 0x18]
    mov edi, [edi]
    mov esi, edi
    xor eax, eax
    mov ecx, NEW_SIZE
    cld
    rep stosb
    push dword [ebp - 4]
    push dword [ebp + 0x14]
    push esi
    call READ_FILE
    add esp, 12
    cmp dword [ebp - 4], NEW_SIZE
    je .check_dates

    ; Preserve flags before moving the overlapping cloud array backwards.
    mov ax, [esi + 0x318]
    mov [esi + FLAGS], ax
    push esi
    lea edi, [esi + CLOUDS + 259]
    add esi, 0x214 + 259
    mov ecx, 260
    std
    rep movsb
    cld
    pop esi
    lea edi, [esi + 0x214]
    mov ecx, 280
    xor eax, eax
    rep stosb

    ; Original files retain the original per-scenario weather origins.
    mov eax, [cs:ebx + 0x2f861] ; relocated Scenario cell address
    mov eax, [eax]
    movzx eax, byte [eax + 0x1220]
    cmp eax, 6
    ja bad_weather
    movzx edx, word [cs:ebx + native_dates + eax * 4]
    or edx, 0x10000
    mov [esi + START], edx
    movzx edx, word [cs:ebx + native_dates + eax * 4 + 2]
    or edx, 0x10000
    mov [esi + END], edx
.check_dates:
    mov eax, [esi + END]
    sub eax, [esi + START]
    cmp eax, 399
    ja bad_weather           ; also rejects a negative interval
    leave_fn

set_dates:
    enter 0
    weather_cell esi
    mov esi, [esi]
    mov edi, [cs:ebx + 0x2f889] ; relocated weather-start global address
    mov eax, [esi + START]
    mov [edi], eax
    add edi, 4               ; adjacent weather-end global, checked by builder
    mov eax, [esi + END]
    mov [edi], eax
    leave_fn

validate_weather:
    enter 4
    mov dword [ebp - 4], 0
    lea eax, [ebp - 4]
    push eax
    movsx eax, word [ebp + 0x14]
    push eax
    call read_weather
    add esp, 8
    mov esi, [ebp - 4]
    weather_cell edi
    mov edi, [edi]
    ; Preserve the original PBEM validator's ground/state comparisons.
    mov ecx, 3
    cld
    repe cmpsd
    jne bad_weather
    mov ax, [esi + FLAGS - 12]
    cmp ax, [edi + FLAGS - 12]
    jne bad_weather
    lea eax, [ebp - 4]
    push eax
    call DISPOSE_PTR
    add esp, 4
    leave_fn

swap_weather:
    enter 0, 0
    mov esi, [ebp + 0x14]
    mov edi, 3
.longs:
    push esi
    call 0x2714f             ; scLong
    add esp, 4
    add esi, 4
    dec edi
    jnz .longs
    mov edi, 400
.shorts:
    push esi
    call 0x2711a             ; scShort
    add esp, 4
    add esi, 2
    dec edi
    jnz .shorts
    add esi, 402             ; skip 400 clouds and two flags
    push esi
    call 0x2714f
    add esp, 4
    add esi, 4
    push esi
    call 0x2714f
    add esp, 4
    leave_fn

bad_weather:
    push 1
    push dword [cs:ebx + 0x27e5a] ; existing fatal weather-read error string
    call DEBUG_STR
    add esp, 8
    call EXIT_SHELL
    ud2

native_dates:
dw 97392-65536, 97409-65536, 97392-65536, 97421-65536
dw 97518-65536, 97621-65536, 97644-65536, 97685-65536
dw 97350-65536, 97523-65536, 97350-65536, 97523-65536, 97350-65536, 97523-65536

; Entered from bg_stuff immediately before its epilogue.
; Override the returned orders for a unit by its authored HQ, not the
; dynamically rebuilt battlegroup number at OB+82h.
; EBX code base is position independent; global operands are loader relocated.
authored_ai:
    pushad
    sub esp, 44
    call code_base
    mov esi, [cs:ebx+0x4d237] ; Scenario pointer cell
    mov esi, [esi]
    mov eax, [cs:ebx+0x4fe52] ; Calendar pointer cell
    mov eax, [eax]
    mov eax, [eax+12]
    sub eax, [esi+0x44]
    inc eax
    mov [esp+36], eax
    mov edi, [ebp+0x14]     ; unit whose orders bg_stuff is returning
    ; Save the working volume and use the game's root, like Turn1Script.
    lea eax, [esp+16]
    push eax
    push byte 0
    call 0x86dc6            ; GetVol
    add esp, 8
    mov eax, [cs:ebx+0x4d19d] ; relocated current game volume operand
    movsx eax, word [eax]
    push eax
    push byte 0
    call 0x86e4d            ; SetVol
    add esp, 8
    mov dword [esp+20], 'WAWA'
    mov dword [esp+24], 'I.DA'
    mov word [esp+28], 'T'
    lea eax, [esp+20]
    push dword 0x200        ; O_RDONLY | O_BINARY
    push eax
    call 0x8f3bf            ; open
    add esp, 8
    test eax, eax
    js .restore
    mov [esp+32], eax
    mov dword [esp+40], 256
.next:
    dec dword [esp+40]
    js .close
    mov eax, esp
    push byte 16
    push eax
    push dword [esp+40]
    call 0x8f15f            ; read
    add esp, 12
    cmp eax, 16
    jne .close
    mov al, [esi+0x1220]
    cmp al, [esp]
    jne .next
    mov al, [edi+0x74]
    cmp al, [esp+2]
    jne .next
    mov al, [edi+0x81]
    cmp al, [esp+4]
    jne .next
    mov eax, [esp+36]
    cmp ax, [esp+6]
    jl .next
    cmp ax, [esp+8]
    jg .next
    movzx eax, word [esp+10]
    cmp eax, 8
    ja .next
    ; Bounds-check the goal against the playable map rectangle.
    mov ax, [esp+12]
    cmp ax, [esi+0x226]
    jl .next
    cmp ax, [esi+0x22a]
    jge .next
    mov ax, [esp+14]
    cmp ax, [esi+0x224]
    jl .next
    cmp ax, [esi+0x228]
    jge .next
    ; High scenario byte: 0 timed; 1/2 objective held by Allied/Axis;
    ; 3/4 Allied/Axis losses >= the argument in side/HQ high bytes.
    mov al, [esp+1]
    test al, al
    jz .apply
    movzx ecx, byte [esp+3]
    mov ch, [esp+5]
    cmp al, 2
    ja .losses
    movzx edx, byte [esi+0x1222]
    cmp ecx, edx
    jae .next
    mov edx, [cs:ebx+0x52ebe] ; relocated VicLoc pointer cell
    mov edx, [edx]
    imul ecx, 48
    dec al
    cmp al, [edx+ecx+17]
    jne .next
    jmp .apply
.losses:
    sub al, 3
    cmp al, 1
    ja .next
    xor al, 1               ; casualty points are credited to the OTHER side
    movzx eax, al
    imul eax, 824            ; v4: expanded victory history stride
    mov edx, [cs:ebx+0x52dd9] ; relocated Victory pointer cell
    mov edx, [edx]
    mov edx, [edx+eax+20]    ; casualty score in thousandths, not total victory
    imul ecx, 1000
    cmp edx, ecx
    jb .next
.apply:
    mov ax, [esp+10]
    mov edx, [ebp+0x18]
    mov [edx], ax           ; authored order
    mov edx, [ebp+0x1c]
    mov [edx], ax           ; effective order
    mov ax, [esp+12]
    mov edx, [ebp+0x20]
    mov [edx], ax
    mov ax, [esp+14]
    mov edx, [ebp+0x24]
    mov [edx], ax
    ; Valid authoring has one matching phase. Stop after a match.
.close:
    push dword [esp+32]
    call 0x8f635            ; replaced with verified close address
    add esp, 4
.restore:
    movsx eax, word [esp+16]
    push eax
    push byte 0
    call 0x86e4d
    add esp, 8
    add esp, 44
    popad
    mov esp, ebp
    pop ebp
    pop edi
    pop esi
    jmp 0x67b5a            ; original POP EBX / RET
