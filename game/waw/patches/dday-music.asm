; Optional V4V FM background music, independent of WAV effects and player prefs.
; Payload: WAM1, uint16 rate=100/reserved=0, uint32 count, (reg,value,delay16)[]
BITS 32
ORG 0xbc000

dd music_sync, music_menu, music_toggle, music_shutdown, music_tick
 dd state_data, state_cursor, state_end, state_wait, state_running
 dd state_enabled, state_service, state_attempted, state_menu, code_end, state_phase

%macro bases 0
    call %%pc
%%pc:
    pop ebx
    sub ebx, %%pc
    mov edi, [cs:ebx+0x26fc1]
    sub edi, 0x7d5f
%endmacro

music_sync:
    pushfd
    pushad
    bases
    cmp byte [ebx+state_attempted], 0
    jne .sync
    mov byte [ebx+state_attempted], 1
    cmp word [edi+0x155e6], 1 ; verified Sound Blaster/AdLib hardware only
    jne .done
    cmp word [edi+0x928c], 0 ; native InitMusic installed the timer successfully
    je .done
    call load_music
    cmp dword [ebx+state_data], 0
    je .done
    push byte 1 ; start paused
    push byte 8 ; service priority
    push byte 0 ; native timer rate (140 Hz); avoid fractional TSM scheduling
    lea eax, [ebx+music_tick]
    push eax
    call 0x8a150 ; TSM_NewService
    add esp, 16
    mov [ebx+state_service], eax
    cmp eax, -1
    je .free
.sync:
    cmp dword [ebx+state_service], -1
    je .done
    cmp byte [ebx+state_enabled], 0
    je .pause
    cmp byte [ebx+state_running], 0
    jne .done
    mov eax, [ebx+state_data]
    add eax, 12
    mov [ebx+state_cursor], eax
    mov dword [ebx+state_wait], 0
    mov dword [ebx+state_phase], 0
    mov byte [ebx+state_running], 1
    push dword [ebx+state_service]
    call 0x89fdc ; TSM_ResumeService
    add esp, 4
    jmp .done
.pause:
    call pause_music
    jmp .done
.free:
    push dword [ebx+state_data]
    call 0x89f4c ; free
    add esp, 4
    mov dword [ebx+state_data], 0
.done:
    ; InsertMenu clears the native enabled mask after GetMenu returns.
    ; SongLogic runs again once the menus have been installed.
    cmp dword [ebx+state_menu], 0
    je .return
    call mark_music
.return:
    popad
    popfd
    ret

pause_music:
    cmp byte [ebx+state_running], 0
    je .done
    push dword [ebx+state_service]
    call 0x8a0c4 ; TSM_PauseService
    add esp, 4
    mov byte [ebx+state_running], 0
    call silence
.done:
    ret

music_shutdown:
    pushad
    bases
    call pause_music
    push dword [ebx+state_service]
    call 0x8a200 ; TSM_DelService also accepts -1
    add esp, 4
    mov dword [ebx+state_service], -1
    mov eax, [ebx+state_data]
    test eax, eax
    jz .done
    push eax
    call 0x89f4c
    add esp, 4
    mov dword [ebx+state_data], 0
.done:
    popad
    jmp 0x8165f ; original KillAllSounds

; Timer callback: bounded work, no DOS I/O or allocations in interrupt context.
music_tick:
    pushfd
    pushad
    bases
    cmp byte [ebx+state_running], 0
    je .done
    ; Native TSM runs at 140 Hz. Its fractional-rate remainder calculation
    ; is not exact for 100 Hz. Request one call per IRQ and divide explicitly.
    add dword [ebx+state_phase], 100
    mov eax, [edi+0x15894]
    cmp [ebx+state_phase], eax
    jb .done
    sub [ebx+state_phase], eax
    cmp dword [ebx+state_wait], 0
    je .play
    dec dword [ebx+state_wait]
    jnz .done
.play:
    mov esi, [ebx+state_cursor]
    mov ecx, 512
.next:
    cmp esi, [ebx+state_end]
    jb .event
    mov esi, [ebx+state_data]
    add esi, 12
.event:
    mov ax, [esi]
    call opl_write
    movzx eax, word [esi+2]
    add esi, 4
    mov [ebx+state_cursor], esi
    mov [ebx+state_wait], eax
    test eax, eax
    jnz .done
    loop .next
    mov byte [ebx+state_running], 0
    call silence
.done:
    popad
    popfd
    ; TSM callback ABI: zero advances the next deadline; 2 reprograms PIT.
    ; Restoring the interrupted EAX here kept the old deadline perpetually due.
    xor eax, eax
    ret

; AL = OPL register, AH = value. OPL2 address/data settle delays.
opl_write:
    push eax
    push ecx
    push edx
    mov dx, 0x388
    out dx, al
    mov ecx, 6
.address_delay:
    in al, dx
    loop .address_delay
    mov al, ah
    inc dx
    out dx, al
    dec dx
    mov ecx, 35
.data_delay:
    in al, dx
    loop .data_delay
    pop edx
    pop ecx
    pop eax
    ret

silence:
    mov ax, 0x00b0
.next:
    call opl_write
    inc al
    cmp al, 0xb9
    jb .next
    mov ax, 0x00bd ; also stop rhythm/percussion voices
    call opl_write
    ret

load_music:
    ; Absolute DOS paths based on the game's installation directory.
    push edi
    lea eax, [edi+0x15444]
    push eax
    lea eax, [ebx+music_path]
    push eax
    call 0x8561a ; strcpy
    add esp, 8
    lea eax, [ebx+music_suffix]
    push eax
    lea eax, [ebx+music_path]
    push eax
    call 0x8778b ; strcat
    add esp, 8
    pop edi
    push 0x200
    lea eax, [ebx+music_path]
    push eax
    call 0x8f3bf ; open
    add esp, 8
    cmp eax, -1
    je .done
    mov esi, eax
    push byte 2
    push byte 0
    push esi
    call 0x8f88f ; lseek
    add esp, 12
    cmp eax, 16
    jb .close
    cmp eax, 1048576
    ja .close
    mov [ebx+state_size], eax
    push eax
    call 0x8cc78 ; malloc
    add esp, 4
    test eax, eax
    jz .close
    mov [ebx+state_data], eax
    push byte 0
    push byte 0
    push esi
    call 0x8f88f
    add esp, 12
    test eax, eax
    jnz .bad_close
    push dword [ebx+state_size]
    push dword [ebx+state_data]
    push esi
    call 0x8f15f ; read
    add esp, 12
    cmp eax, [ebx+state_size]
    jne .bad_close
    push esi
    call 0x8f635
    add esp, 4
    mov esi, [ebx+state_data]
    cmp dword [esi], 'WAM1'
    jne .bad
    cmp dword [esi+4], 100
    jne .bad
    mov eax, [ebx+state_size]
    sub eax, 12
    test al, 3
    jnz .bad
    shr eax, 2
    cmp eax, [esi+8]
    jne .bad
    mov ecx, eax
    mov eax, [ebx+state_size]
    add eax, esi
    mov [ebx+state_end], eax
    cmp word [eax-2], 0 ; guarantees a delay across the playlist wrap
    je .bad
    add esi, 12
    xor edx, edx
.validate:
    inc edx
    cmp edx, 512
    ja .bad
    mov al, [esi]
    cmp al, 1
    je .allowed
    cmp al, 8
    je .allowed
    cmp al, 0x20
    jb .bad
    cmp al, 0xf5
    ja .bad
.allowed:
    cmp word [esi+2], 0
    je .advance
    xor edx, edx
.advance:
    add esi, 4
    loop .validate
    ; Read persistent music switch; missing/invalid file defaults to on.
    lea eax, [edi+0x15444]
    push eax
    lea eax, [ebx+config_path]
    push eax
    call 0x8561a
    add esp, 8
    lea eax, [ebx+config_suffix]
    push eax
    lea eax, [ebx+config_path]
    push eax
    call 0x8778b
    add esp, 8
    push 0x200
    lea eax, [ebx+config_path]
    push eax
    call 0x8f3bf
    add esp, 8
    cmp eax, -1
    je .done
    mov esi, eax
    push byte 1
    lea eax, [ebx+config_byte]
    push eax
    push esi
    call 0x8f15f
    add esp, 12
    cmp eax, 1
    jne .close
    cmp byte [ebx+config_byte], '0'
    jne .close
    mov byte [ebx+state_enabled], 0
.close:
    push esi
    call 0x8f635
    add esp, 4
.done:
    ret
.bad_close:
    push esi
    call 0x8f635
    add esp, 4
.bad:
    push dword [ebx+state_data]
    call 0x89f4c
    add esp, 4
    mov dword [ebx+state_data], 0
    ret

; GetMenu(130) call wrapper: append item 18 without altering the resource file.
music_menu:
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi
    sub esp, 8
    push dword [ebp+8]
    call 0x8343d ; original GetMenu
    add esp, 4
    mov [ebp-16], eax
    push eax
    call 0x81ad2 ; GetHandleSize
    add esp, 4
    mov [ebp-20], eax
    add eax, menu_item_end-menu_item-1
    push eax
    call 0x81936 ; nucNewHandle
    add esp, 4
    mov esi, [ebp-16]
    mov esi, [esi]
    mov edi, [eax]
    mov ecx, [ebp-20]
    dec ecx ; replace the terminating zero
    cld
    rep movsb
    push eax
    bases
    lea esi, [ebx+menu_item]
    pop eax
    ; bases changed EDI: recompute the new end-of-menu destination.
    mov edi, [eax]
    add edi, [ebp-20]
    dec edi
    mov ecx, menu_item_end-menu_item
    rep movsb
    mov [ebx+state_menu], eax
    push eax
    call 0x83271 ; CalcMenuSize
    add esp, 4
    call mark_music
    mov eax, [ebx+state_menu]
    add esp, 8
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret

music_toggle:
    cmp word [esp+4], 18
    je .toggle
    ; Original prologue, then resume the untouched option dispatcher.
    push ebx
    push esi
    push edi
    push ebp
    mov ebp, esp
    jmp 0x41de8
.toggle:
    pushad
    bases
    cmp dword [ebx+state_service], -1
    je .done
    xor byte [ebx+state_enabled], 1
    call music_sync
    call mark_music
    mov al, [ebx+state_enabled]
    add al, '0'
    mov [ebx+config_byte], al
    push 0x180
    push 0x261
    lea eax, [ebx+config_path]
    push eax
    call 0x8f3bf
    add esp, 12
    cmp eax, -1
    je .done
    mov esi, eax
    push byte 1
    lea eax, [ebx+config_byte]
    push eax
    push esi
    call 0x8f643 ; write
    add esp, 12
    push esi
    call 0x8f635
    add esp, 4
.done:
    popad
    ret

mark_music:
    bases
    cmp dword [ebx+state_service], -1
    je .disabled
    movzx eax, byte [ebx+state_enabled]
    movzx eax, byte [edi+eax+0x7c63]
    push eax
    push byte 18
    push dword [ebx+state_menu]
    call 0x83618 ; SetItemMark
    add esp, 12
    push byte 18
    push dword [ebx+state_menu]
    call 0x835ed ; EnableItem
    add esp, 8
    ret
.disabled:
    push byte 18
    push dword [ebx+state_menu]
    call 0x835b4 ; DisableItem
    add esp, 8
    ret

align 4
state_data: dd 0
state_cursor: dd 0
state_end: dd 0
state_wait: dd 0
state_size: dd 0
state_phase: dd 0
state_service: dd -1
state_menu: dd 0
state_running: db 0
state_enabled: db 1
state_attempted: db 0
config_byte: db '1'
music_suffix: db '\data\music\v4v.opl',0
config_suffix: db '\data\music\music.cfg',0
menu_item: db 16,'Background Music',0,0,0,0,0
menu_item_end:
music_path: times 128 db 0
config_path: times 128 db 0
code_end:
