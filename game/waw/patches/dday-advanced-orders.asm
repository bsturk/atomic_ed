; Included only with ADVANCED_ORDERS=1. Keep earlier patch layers identical.
; WAWAI003: 32-byte fingerprinted header, then up to 256 32-byte rows.
; Persistent bits mean "this plan has supplied an order", not first-unit-only
; events. Every member of the HQ continues to receive the latched directive.

; cdecl(fd, header): 1 advanced, 0 legacy/missing header, -1 invalid advanced.
events_read_header:
    enter_fn 4
    push byte 32
    push dword [ebp+0x18]
    push dword [ebp+0x14]
    call READ
    add esp, 12
    cmp eax, 8
    jl .legacy
    mov esi, [ebp+0x18]
    cmp dword [esi], 'WAWA'
    jne .legacy
%ifdef NESTED_EVENTS
    cmp dword [esi+4], 'I004'
    je .nested
%endif
    cmp dword [esi+4], 'I003'
    jne .legacy
    cmp eax, 32
    jne .bad
    cmp word [esi+10], 32
    jne .bad
%ifdef NESTED_EVENTS
    jmp .common
.nested:
    cmp eax,32
    jne .bad
    cmp word [esi+10],320
    jne .bad
.common:
%endif
    cmp word [esi+16], 0xffff
    jne .bad
    cmp word [esi+30], 0
    jne .bad
    movzx eax, word [esi+8]
    dec eax
    cmp eax, 255
    ja .bad
    inc eax
%ifdef NESTED_EVENTS
    movzx ecx,word [esi+10]
    imul eax,ecx
%else
    shl eax, 5
%endif
    add eax, 32
    mov [ebp-4], eax
    push byte 2
    push byte 0
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    cmp eax, [ebp-4]
    jne .bad
    push byte 0
    push byte 32
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    cmp eax, 32
    jne .bad
    mov eax, 1
    leave_fn
.legacy:
    xor eax, eax
    leave_fn
.bad:
    or eax, -1
    leave_fn

; Fresh game/resume: zero the flags and read the current companion identity.
; Return 1 for valid advanced/legacy files, 0 for malformed advanced files.
events_initialize:
    enter_fn 44
    xor eax, eax
    mov ecx, 64
.clear:
    dec ecx
    mov [ebx+event_key+ecx], al
    jnz .clear
    mov dword [ebp-12], 1
    lea eax, [ebp-4]
    call home_volume
    push 0x200
    lea eax, [ebx+events_default_path]
    push eax
    call open_orders
    add esp, 8
    test eax, eax
    js .volume
    mov [ebp-8], eax
    lea ecx, [ebp-44]
    push ecx
    push eax
    call events_read_header
    add esp, 8
    test eax, eax
    jz .close
    js .invalid
    xor ecx, ecx
.copy:
    mov eax, [ebp-44+ecx]
    mov [ebx+event_key+ecx], eax
    add ecx, 4
    cmp ecx, 32
    jb .copy
%ifdef NESTED_EVENTS
    cmp dword [ebx+event_key+4],'I004'
    jne .close
    push byte 0
    push byte 0
    push byte 0
    call nested_process
    add esp,12
    test eax,eax
    js .invalid
%endif
    jmp .close
.invalid:
    mov dword [ebp-12], 0
.close:
    push dword [ebp-8]
    call CLOSE
    add esp, 4
.volume:
    movsx eax, word [ebp-4]
    push eax
    push byte 0
    call 0x86e4d
    add esp, 8
    mov eax, [ebp-12]
    leave_fn

; cdecl(save_fd). The 80-byte event footer precedes the existing 64-byte
; library identity. Preserve the native scenario reader's file position.
events_restore:
    enter_fn 88
    mov dword [ebp-88], 1
    push byte 1
    push byte 0
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    mov [ebp-4], eax
    push byte 2
    push dword -144
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    test eax, eax
    js .position
    push byte 80
    lea eax, [ebp-84]
    push eax
    push dword [ebp+0x14]
    call READ
    add esp, 12
    cmp eax, 80
    jne .position
    cmp dword [ebp-84], 'WAWE'
    jne .position
    cmp dword [ebp-80], 'VT01'
    jne .position
    cmp dword [ebp-12], 'WAWE'
    jne .bad
    cmp dword [ebp-8], 'VT01'
    jne .bad
    cmp dword [ebx+event_key], 'WAWA'
    jne .bad
    xor ecx, ecx
.compare:
    mov eax, [ebp-76+ecx]
    cmp eax, [ebx+event_key+ecx]
    jne .bad
    add ecx, 4
    cmp ecx, 32
    jb .compare
    xor ecx, ecx
.copy:
    mov eax, [ebp-44+ecx]
    mov [ebx+event_bits+ecx], eax
    add ecx, 4
    cmp ecx, 32
    jb .copy
    jmp .position
.bad:
    mov dword [ebp-88], 0
.position:
    push byte 0
    push dword [ebp-4]
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    cmp eax, [ebp-4]
    jne .bad_position
    mov eax, [ebp-88]
    leave_fn
.bad_position:
    xor eax, eax
    leave_fn

; cdecl(row, scenario). Return 1/0, or -1 for a malformed condition.
; Evaluate every clause so ANY cannot conceal an invalid later clause.
events_conditions:
    enter_fn 12
    mov esi, [ebp+0x14]
    movzx eax, byte [esi+18]
    cmp eax, 1
    ja .invalid
    mov [ebp-8], eax
    xor eax, 1
    mov [ebp-12], eax
    movzx eax, byte [esi+19]
    cmp eax, 3
    ja .invalid
    test eax, eax
    jz .always
    mov [ebp-4], eax
    add esi, 20
.next:
    movzx eax, byte [esi+1]
    cmp eax, 1
    ja .invalid
    movzx ecx, word [esi+2]
    cmp byte [esi], 1
    jne .losses
    mov edx, [ebp+0x18]
    movzx edx, byte [edx+0x1222]
    cmp ecx, edx
    jae .invalid
    mov edx, [edi+0x7d53]
    test edx, edx
    jz .invalid
    imul ecx, 48
    cmp al, [edx+ecx+17]
    sete al
    movzx eax, al
    jmp .combine
.losses:
    cmp byte [esi], 2
    jne .invalid
    test ecx, ecx
    jz .invalid
    xor eax, 1
    imul eax, 824
    mov edx, [edi+0x7d57]
    test edx, edx
    jz .invalid
    mov edx, [edx+eax+20]
    imul ecx, 1000
    cmp edx, ecx
    setae al
    movzx eax, al
.combine:
    cmp dword [ebp-8], 0
    jne .any
    and [ebp-12], eax
    jmp .step
.any:
    or [ebp-12], eax
.step:
    add esi, 4
    dec dword [ebp-4]
    jnz .next
    mov eax, [ebp-12]
    leave_fn
.always:
    mov eax, 1
    leave_fn
.invalid:
    or eax, -1
    leave_fn

; Hook bg_stuff's epilogue, just as the original authored-order patch does.
; Legacy files delegate to that unchanged implementation with its original
; frame/registers. The native tactical mode is never overwritten.
advanced_orders:
%ifdef NESTED_EVENTS
    pushad
    call bases
    cmp dword [ebx+event_key+4],'I004'
    popad
    je nested_orders
%endif
    pushad
    mov ebp, esp
    sub esp, 112
    call bases
    mov eax, [ebp+8]             ; original bg_stuff frame
    mov eax, [eax+0x14]
    mov [ebp-12], eax           ; unit
    mov eax, [edi+0x7d5f]
    mov [ebp-16], eax           ; Scenario
    mov edx, [edi+0x7d63]
    mov edx, [edx+12]
    sub edx, [eax+0x44]
    inc edx
    mov [ebp-20], edx           ; relative turn
    mov dword [ebp-100], 0      ; delegate legacy flag
    lea eax, [ebp-8]
    call home_volume
    push 0x200
    lea eax, [ebx+events_default_path]
    push eax
    call open_orders
    add esp, 8
    test eax, eax
    js .restore
    mov [ebp-4], eax
    lea ecx, [ebp-64]
    push ecx
    push eax
    call events_read_header
    add esp, 8
    test eax, eax
    js .close
    jnz .advanced
    mov dword [ebp-100], 1
    jmp .close
.advanced:
    ; The key is initialized by LoadGame. Never reuse bits against changed
    ; rules, including a companion replaced while the game is running.
    xor ecx, ecx
.compare:
    mov eax, [ebp-64+ecx]
    cmp eax, [ebx+event_key+ecx]
    jne .close
    add ecx, 4
    cmp ecx, 32
    jb .compare
    movzx eax, word [ebp-56]
    mov [ebp-28], eax
    mov dword [ebp-24], -1
.next:
    inc dword [ebp-24]
    mov eax, [ebp-24]
    cmp eax, [ebp-28]
    jae .close
    push byte 32
    lea eax, [ebp-96]
    push eax
    push dword [ebp-4]
    call READ
    add esp, 12
    cmp eax, 32
    jne .close
    mov esi, [ebp-12]
    mov edx, [ebp-16]
    cmp word [ebp-80], 0xffff
    jne .next
    mov al, [ebp-95]
    and al, 0xfe
    cmp al, 0x80
    jne .next
    mov al, [edx+0x1220]
    cmp al, [ebp-96]
    jne .next
    movzx eax, byte [esi+0x74]
    cmp ax, [ebp-94]
    jne .next
    movzx eax, byte [esi+0x81]
    cmp ax, [ebp-92]
    jne .next
    mov eax, [ebp-20]
    cmp word [ebp-90], 1
    jl .next
    cmp ax, [ebp-90]
    jl .next
    cmp ax, [ebp-88]
    jg .next
    mov ax, [ebp-86]
    cmp ax, 1
    je .goal
    cmp ax, 3
    je .goal
    sub ax, 6
    cmp ax, 2
    ja .next
.goal:
    mov ax, [ebp-84]
    cmp ax, [edx+0x226]
    jl .next
    cmp ax, [edx+0x22a]
    jge .next
    mov ax, [ebp-82]
    cmp ax, [edx+0x224]
    jl .next
    cmp ax, [edx+0x228]
    jge .next
    push edx
    lea eax, [ebp-96]
    push eax
    call events_conditions
    add esp, 8
    test eax, eax
    js .next
    jnz .apply
    cmp byte [ebp-95], 0x81
    jne .next
    mov eax, [ebp-24]
    bt [ebx+event_bits], eax
    jnc .next
.apply:
    cmp byte [ebp-95], 0x81
    jne .outputs
    mov eax, [ebp-24]
    bts [ebx+event_bits], eax
.outputs:
    mov ecx, [ebp+8]
    mov ax, [ebp-86]
    mov edx, [ecx+0x18]
    mov [edx], ax
    mov edx, [ecx+0x1c]
    mov [edx], ax
    mov ax, [ebp-84]
    mov edx, [ecx+0x20]
    mov [edx], ax
    mov ax, [ebp-82]
    mov edx, [ecx+0x24]
    mov [edx], ax
.close:
    push dword [ebp-4]
    call CLOSE
    add esp, 4
.restore:
    movsx eax, word [ebp-8]
    push eax
    push byte 0
    call 0x86e4d
    add esp, 8
    cmp dword [ebp-100], 0
    jne .legacy
    mov esp, ebp
    popad
    mov esp, ebp
    pop ebp
    pop edi
    pop esi
    jmp 0x67b5a
.legacy:
    mov esp, ebp
    popad
    jmp 0xb2e21                  ; unchanged version-4 AuthoredAI

events_default_path: db 'WAWAI.DAT',0
events_error: db 'Cannot load battle plans. Restore the matching AI file for this save, or start a new game.',0
align 4
event_state: db 'WAWEVT01'
event_key: times 32 db 0
event_bits: times 32 db 0
db 'WAWEVT01'
