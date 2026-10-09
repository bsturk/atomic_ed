; Dynamic scenarios in the existing seven-row options panel. NASM -f bin.
; Loaded in added LE pages. Existing object-relative addresses stay unchanged.
BITS 32
ORG 0xb3000

%define OPEN 0x8f3bf
%define READ 0x8f15f
%define CLOSE 0x8f635
%define SEEK 0x8f88f
%define COPY 0x8561a
%define LIMIT 256
%define RECORD 64

dd initial_preview, select_row, init_secondary, draw_label
dd get_resource, load_identity, save_identity, open_orders
dd state_count, state_selected, state_page, active, records, identifiers
dd refresh_rows, scan, native_read, native_resource, native_secondary
dd code_end
%ifdef CUSTOM_ARTWORK
dd leader_portrait
%endif
%ifdef ADVANCED_ORDERS
dd advanced_orders, events_initialize, events_restore, event_state, events_conditions
%endif
%ifdef SUPPORT_ARTWORK
dd more_air_support, initial_plane_category, initial_ship_category
%endif

%ifdef GAME_PROFILES
    dd profile_victory, profile_ground, game_rules, read_game_rules
%endif

%ifdef TERRAIN_RULES
    dd terrain_base_cost, terrain_defense, terrain_barrage, terrain_rules, read_terrain_rules, commit_terrain_rules
%endif

%ifdef NESTED_EVENTS
    dd nested_process, nested_conditions, nested_read_row, nested_start, nested_turn
    dd nested_message, nested_draw_message, nested_message_cursor
%endif

%macro enter_fn 1
    push ebx
    push esi
    push edi
    push ebp
    mov ebp, esp
    sub esp, %1
    call bases
%endmacro
%macro leave_fn 0
    mov esp, ebp
    pop ebp
    pop edi
    pop esi
    pop ebx
    ret
%endmacro

%ifdef SUPPORT_ARTWORK
; OpenPSBox sets the category picture before skipping empty classes. Select
; first, then set the picture to match the actual roster that will be drawn.
initial_plane_category:
    enter_fn 0
    call 0x5c8cd
    movzx eax, byte [edi+0x8037]
    shl eax, 2
    add ax, [edi+0x13278]
    add eax, 23
    mov [edi+0x10ac7], ax
    leave_fn

initial_ship_category:
    enter_fn 0
    call 0x57be7
    mov ax, [edi+0x10130]
    add ax, 31
    mov [edi+0x10ac7], ax
    leave_fn

; The native optional air-support bonus doubles availability and then asserts
; it fits the roster. Custom categories may have only one squadron. Cap the
; bonus at the actual category count; stock scenarios retain their old result.
more_air_support:
    enter_fn 0
    mov eax, [edi+0x7d5f]
    movzx edx, byte [eax+0x1229]
    cmp edx, 4
    ja .done
    xor ecx, ecx
.category:
    imul esi, ecx, 10
    lea esi, [edi+esi+0x127b4]
    movsx eax, word [esi+edx*2]
    add eax, eax
    movsx ebx, word [edi+ecx*2+0x7e9b]
    cmp eax, ebx
    jle .store
    mov eax, ebx
.store:
    mov [esi+edx*2], ax
    inc ecx
    cmp ecx, 2
    jb .category
.done:
    leave_fn
%endif

bases:
    call .pc
.pc:
    pop ebx
    sub ebx, .pc
    mov edi, [cs:ebx+0x26fc1] ; loader-relocated Scenario pointer operand
    sub edi, 0x7d5f
    ret

; Use the game's own volume API, preserving the caller's working directory.
home_volume:
    push eax
    push byte 0
    call 0x86dc6
    add esp, 8
    movsx eax, word [edi+0x1314c]
    push eax
    push byte 0
    call 0x86e4d
    add esp, 8
    ret

; Read a footer without changing the file position. cdecl(fd, destination).
peek_footer:
    enter_fn 8
%ifdef TERRAIN_RULES
    mov eax, [ebp+0x18]
    mov dword [eax], 0
%endif
    push byte 1
    push byte 0
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    mov [ebp-4], eax
    push byte 2
    push byte -64
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    test eax, eax
    js .bad
    push byte 64
    push dword [ebp+0x18]
    push dword [ebp+0x14]
    call READ
    add esp, 12
    cmp eax, 64
    jne .bad
    mov esi, [ebp+0x18]
    cmp dword [esi], 'WAWL'
    jne .bad
    cmp dword [esi+4], 'IB01'
    jne .bad
    cmp dword [esi+56], 'WAWL'
    jne .bad
    cmp dword [esi+60], 'IB01'
    jne .bad
%ifdef TERRAIN_RULES
    cmp dword [esi+48], 7
    je .flags_ok
%endif
%ifdef GAME_PROFILES
    cmp dword [esi+48], 2
    je .bad
    cmp dword [esi+48], 3
%else
    cmp dword [esi+48], 1
%endif
    ja .bad
%ifdef TERRAIN_RULES
.flags_ok:
%endif
    cmp dword [esi+52], 0
    jne .bad
    cmp byte [esi+20], 0
    jne .bad
    cmp byte [esi+47], 0
    jne .bad
    mov eax, 1
    jmp .restore
.bad:
    xor eax, eax
.restore:
    mov [ebp-8], eax
    push byte 0
    push dword [ebp-4]
    push dword [ebp+0x14]
    call SEEK
    add esp, 12
    mov eax, [ebp-8]
    leave_fn

; cdecl(destination, filename). Construct SCENARIO\ plus a bounded DOS name.
make_path:
    enter_fn 0
    mov esi, [ebp+0x14]
    lea eax, [ebx+folder]
    push eax
    push esi
    call COPY
    add esp, 8
    add esi, 9
    push dword [ebp+0x18]
    push esi
    call COPY
    add esp, 8
    leave_fn

; Fill metadata with a filename-derived title, replacing native names with
; their original full titles. cdecl(record, filename).
default_record:
    enter_fn 0
    mov esi, [ebp+0x14]
    push edi
    mov edi, esi
    xor eax, eax
    mov ecx, 16
    rep stosd
    pop edi
    mov dword [esi], 'WAWL'
    mov dword [esi+4], 'IB01'
    mov dword [esi+56], 'WAWL'
    mov dword [esi+60], 'IB01'
    push dword [ebp+0x18]
    lea eax, [esi+8]
    push eax
    call COPY
    add esp, 8
    push dword [ebp+0x18]
    lea eax, [esi+21]
    push eax
    call COPY
    add esp, 8
    xor ecx, ecx
.strip:
    cmp byte [esi+21+ecx], '.'
    je .nul
    inc ecx
    cmp ecx, 8
    jb .strip
.nul:
    mov byte [esi+21+ecx], 0
    xor ecx, ecx
.names:
    push ecx
    imul eax, ecx, 13
    lea eax, [ebx+native_names+eax]
    push eax
    push dword [ebp+0x18]
    call 0x8cc22 ; stricmp
    add esp, 8
    pop ecx
    test eax, eax
    jz .native
    inc ecx
    cmp ecx, 7
    jb .names
    jmp .done
.native:
    imul eax, ecx, 26
    lea eax, [ebx+native_titles+eax]
    push eax
    lea eax, [esi+21]
    push eax
    call COPY
    add esp, 8
.done:
    leave_fn

scan:
    enter_fn 56
    cmp dword [ebx+scanned], 0
    jne .done
    mov dword [ebx+scanned], 1
    lea eax, [ebp-4]
    call home_volume
    mov dword [ebx+state_count], 0
    lea eax, [ebp-52]
    push eax
    push byte 0
    lea eax, [ebx+pattern]
    push eax
    call 0x8cb8c
    add esp, 12
    test eax, eax
    jnz .finish
.file:
    cmp dword [ebx+state_count], LIMIT
    jae .full
    lea eax, [ebp-22] ; find_t.name = offset 30
    push eax
    lea eax, [ebx+scratch_path]
    push eax
    call make_path
    add esp, 8
    push 0x200
    lea eax, [ebx+scratch_path]
    push eax
    call OPEN
    add esp, 8
    test eax, eax
    js .next
    mov [ebp-8], eax
    push 0x1262
    lea eax, [ebx+scratch_header]
    push eax
    push dword [ebp-8]
    call READ
    add esp, 12
    cmp eax, 0x1262
    jne .close
    cmp dword [ebx+scratch_header], 0x1230
    jne .close
    cmp dword [ebx+scratch_header+4], 17
    jne .close
    cmp byte [ebx+scratch_header+4+0x1220], 6
    ja .close
    mov eax, [ebx+state_count]
    shl eax, 6
    lea esi, [ebx+records+eax]
    push esi
    push dword [ebp-8]
    call peek_footer
    add esp, 8
    test eax, eax
    jnz .metadata
%ifdef TERRAIN_RULES
    ; A recognized but invalid/future footer must not become an unprofiled SCN.
    cmp dword [esi], 'WAWL'
    je .close
%endif
    lea eax, [ebp-22]
    push eax
    push esi
    call default_record
    add esp, 8
.metadata:
    ; Renaming an SCN is allowed: discovery uses its actual DOS filename.
    lea eax, [ebp-22]
    push eax
    lea eax, [esi+8]
    push eax
    call COPY
    add esp, 8
    mov eax, [ebx+state_count]
    mov dl, [ebx+scratch_header+4+0x1220]
    mov [ebx+identifiers+eax], dl
    inc dword [ebx+state_count]
.close:
    push dword [ebp-8]
    call CLOSE
    add esp, 4
.next:
    lea eax, [ebp-52]
    push eax
    call 0x8cbb9
    add esp, 4
    test eax, eax
    jz .file
    jmp .finish
.full:
    push byte 0
    lea eax, [ebx+full_text]
    push eax
    call 0x24d73
    add esp, 8
.finish:
    movsx eax, word [ebp-4]
    push eax
    push byte 0
    call 0x86e4d
    add esp, 8
    ; Stable insertion sort by DOS filename, carrying compatibility IDs.
    mov dword [ebp-12], 1
.sort_outer:
    mov eax, [ebp-12]
    cmp eax, [ebx+state_count]
    jae .done
    mov [ebp-16], eax
.sort_inner:
    mov eax, [ebp-16]
    test eax, eax
    jz .advance
    shl eax, 6
    lea esi, [ebx+records+eax]
    lea eax, [esi+8]
    push eax
    sub eax, 64
    push eax
    call 0x8cc22
    add esp, 8
    test eax, eax
    jle .advance
    mov ecx, 16
.swap:
    mov eax, [esi]
    mov edx, [esi-64]
    mov [esi-64], eax
    mov [esi], edx
    add esi, 4
    loop .swap
    mov eax, [ebp-16]
    mov dl, [ebx+identifiers+eax]
    xchg dl, [ebx+identifiers+eax-1]
    mov [ebx+identifiers+eax], dl
    dec dword [ebp-16]
    jmp .sort_inner
.advance:
    inc dword [ebp-12]
    jmp .sort_outer
.done:
    leave_fn

; Native seven-row panel: previous, five files, next. Titles are supplied by
; the existing text renderer, leaving other option panels untouched.
refresh_rows:
    enter_fn 4
    mov dword [ebp-4], 0
.row:
    mov ecx, [ebp-4]
    mov byte [edi+0x6fd0+ecx], 1
    imul edx, ecx, 56
    mov byte [edi+0x10fb9+edx], 0
    test ecx, ecx
    jz .previous
    cmp ecx, 6
    je .next
    lea eax, [ecx-1]
    add eax, [ebx+state_page]
    cmp eax, [ebx+state_count]
    jae .disabled
    cmp eax, [ebx+state_selected]
    jne .advance
    mov byte [edi+0x10fb9+edx], 1
    mov [edi+0x6fcd], cl
    jmp .advance
.previous:
    cmp dword [ebx+state_page], 0
    jne .advance
    jmp .disabled
.next:
    mov eax, [ebx+state_page]
    add eax, 5
    cmp eax, [ebx+state_count]
    jb .advance
.disabled:
    mov byte [edi+0x10fb9+edx], 2
    mov byte [edi+0x6fd0+ecx], 0
.advance:
    inc dword [ebp-4]
    cmp dword [ebp-4], 7
    jb .row
    leave_fn

draw_label:
    ; Replacement for DrawCStr(label, x, y) at the scenario-row call site.
    enter_fn 0
    mov eax, [ebp+0x14]
    sub eax, edi
    sub eax, 0x7789
    xor edx, edx
    mov ecx, 26
    div ecx
    lea esi, [ebx+previous_text]
    test eax, eax
    jz .draw
    lea esi, [ebx+next_text]
    cmp eax, 6
    je .draw
    dec eax
    add eax, [ebx+state_page]
    lea esi, [ebx+empty_text]
    cmp eax, [ebx+state_count]
    jae .draw
    shl eax, 6
    lea esi, [ebx+records+eax+21]
.draw:
    push dword [ebp+0x1c]
    push dword [ebp+0x18]
    push esi
    call 0x24f01
    add esp, 12
    leave_fn

init_secondary:
    enter_fn 0
    cmp byte [edi+0x6fcc], 7
    jne .native
    call scan
    call paint_panel
    leave_fn
.native:
    call native_secondary
    leave_fn

initial_preview:
    enter_fn 0
    call scan
%ifdef STARTUP_SELECTION
    call startup_selection
    cmp eax, -1
    je .default
    cmp eax, -2
    je .startup_error
    mov esi, eax
    call activate_index
    test eax, eax
    jnz .done
.startup_error:
    push byte 1
    lea eax, [ebx+startup_error_text]
    push eax
    call 0x24d73
    add esp, 8
    call 0x86288
.default:
%endif
    xor esi, esi
.try:
    cmp esi, [ebx+state_count]
    jae .empty
    mov eax, esi
    call activate_index
    test eax, eax
    jnz .done
    inc esi
    jmp .try
.done:
    mov eax, esi
    xor edx, edx
    mov ecx, 5
    div ecx
    sub esi, edx
    mov [ebx+state_page], esi
    leave_fn
.empty:
    push byte 1
    lea eax, [ebx+empty_library_text]
    push eax
    call 0x24d73
    add esp, 8
    call 0x86288

select_row:
    enter_fn 0
    mov eax, [ebp+0x14]
    test eax, eax
    jz .previous
    cmp eax, 6
    je .next
    dec eax
    add eax, [ebx+state_page]
    cmp eax, [ebx+state_count]
    jae .done
    call activate_index
    test eax, eax
    jz .redraw
    mov byte [edi+0x8047], 1
    mov byte [edi+0x7dc3], 1
    call 0x3dff6
    call 0x3e3e4
    jmp .redraw
.previous:
    cmp dword [ebx+state_page], 0
    je .done
    sub dword [ebx+state_page], 5
    jmp .redraw
.next:
    mov eax, [ebx+state_page]
    add eax, 5
    cmp eax, [ebx+state_count]
    jae .done
    mov [ebx+state_page], eax
.redraw:
    call paint_panel
.done:
    leave_fn

paint_panel:
    enter_fn 4
    call refresh_rows
    push byte -1
    push byte 1
    call 0x3edee
    add esp, 8
    mov dword [ebp-4], 0
.buttons:
    imul eax, [ebp-4], 56
    movzx edx, byte [edi+0x10fb9+eax]
    push edx
    lea eax, [edi+0x10f94+eax]
    push eax
    call 0x19f97
    add esp, 8
    inc dword [ebp-4]
    cmp dword [ebp-4], 7
    jb .buttons
    leave_fn

; Internal EAX=index; retain native scenario ID for engine rules.
activate_index:
    push eax
    push esi
    shl eax, 6
    lea esi, [ebx+records+eax]
    push esi
    call activate_assets
    add esp, 4
    test eax, eax
    jz .failed
    mov eax, [esp+4]
    mov [ebx+state_selected], eax
    movzx eax, byte [ebx+identifiers+eax]
    mov [edi+0x6fce], al
    push eax
    imul eax, 13
    lea eax, [edi+0x783f+eax]
    lea edx, [esi+8]
    push edx
    push eax
    call COPY
    add esp, 8
    call native_read
    add esp, 4
    call preview_bounds
    mov eax, 1
.failed:
    pop esi
    add esp, 4
    ret

; Footer names are single DOS basenames, never paths. Metadata is untrusted.
valid_name:
    push esi
    mov esi, eax
    xor ecx, ecx
.loop:
    mov al, [esi+ecx]
    cmp al, '.'
    je .extension
    cmp al, 33
    jb .bad
    cmp al, 126
    ja .bad
    cmp al, 47
    je .bad
    cmp al, 92
    je .bad
    cmp al, ':'
    je .bad
    inc ecx
    cmp ecx, 8
    jbe .loop
.bad:
    xor eax, eax
    pop esi
    ret
.extension:
    test ecx, ecx
    jz .bad
    cmp dword [esi+ecx], '.SCN'
    jne .bad
    cmp byte [esi+ecx+4], 0
    jne .bad
    mov eax, 1
    pop esi
    ret

; Discard only the scenario overlay. Core fonts, dialogs and their handles
; stay in resource map zero throughout the session.
drop_overlay:
    enter_fn 12
    cmp dword [ebx+overlay], 0
    je .done
    mov esi, [edi+0x14acc]
    movzx eax, word [esi+24]
    add esi, eax
    movzx eax, word [esi]
    inc eax
    mov [ebp-4], eax
    mov [ebp-8], esi
    add esi, 2
.type:
    cmp dword [ebp-4], 0
    je .free_map
    movzx eax, word [esi+6]
    add eax, [ebp-8]
    mov [ebp-12], eax
    movzx ecx, word [esi+4]
    inc ecx
.reference:
    push ecx
    mov eax, [ebp-12]
    mov eax, [eax+8]
    test eax, eax
    jz .empty
    push eax
    call 0x819b6 ; DisposeHandle, map is about to be discarded
    add esp, 4
.empty:
    add dword [ebp-12], 12
    pop ecx
    loop .reference
    add esi, 8
    dec dword [ebp-4]
    jmp .type
.free_map:
    movsx eax, word [edi+0x14ade]
    push eax
    call 0x84838
    add esp, 4
    push dword [edi+0x14acc]
    call 0x81a73
    add esp, 4
    mov dword [edi+0x14acc], 0
    mov word [edi+0x9370], 1
    mov word [edi+0x9372], 0
    mov dword [ebx+overlay], 0
.done:
    leave_fn

; cdecl(record). Probe companions before changing the live resource map.
activate_assets:
%ifdef GAME_PROFILES
    enter_fn 28
    mov dword [ebp-28], 1
%else
    enter_fn 24
%endif
    mov esi, [ebp+0x14]
    lea eax, [esi+8]
    call valid_name
    test eax, eax
    jz .invalid
    lea eax, [ebp-4]
    call home_volume
    lea eax, [esi+8]
    push eax
    lea eax, [ebx+scratch_path]
    push eax
    call make_path
    add esp, 8
    lea eax, [ebx+scratch_path]
    push eax
    call 0x8621d ; strlen
    add esp, 4
    mov [ebp-8], eax
    mov dword [ebx+scratch_path+eax-4], '.REZ'
    push 0x200
    lea eax, [ebx+scratch_path]
    push eax
    call OPEN
    add esp, 8
    mov [ebp-12], eax
    test eax, eax
    jns .check_rez
    test dword [esi+48], 1
    jnz .missing
    jmp .commit
.check_rez:
    push byte 16
    lea eax, [ebx+rez_header]
    push eax
    push dword [ebp-12]
    call READ
    add esp, 12
    mov [ebp-16], eax
%ifdef GAME_PROFILES
    test dword [esi+48], 2
    jz .rules_read
    push dword [ebp-12]
    call read_game_rules
    add esp, 4
    mov [ebp-28], eax
.rules_read:
%ifdef TERRAIN_RULES
    cmp dword [ebp-28], 0
    je .terrain_read
    test dword [esi+48], 4
    jz .terrain_read
    push dword [ebp-12]
    call read_terrain_rules
    add esp, 4
    mov [ebp-28], eax
.terrain_read:
%endif
%endif
    push byte 2
    push byte 0
    push dword [ebp-12]
    call SEEK
    add esp, 12
    mov edx, eax
    push edx
    push dword [ebp-12]
    call CLOSE
    add esp, 4
    pop edx
%ifdef GAME_PROFILES
    cmp dword [ebp-28], 0
    je .missing
%endif
    cmp dword [ebp-16], 16
    jne .missing
    mov eax, [ebx+rez_header+4]
    bswap eax
    mov ecx, [ebx+rez_header+12]
    bswap ecx
    add eax, ecx
    jc .missing
    cmp eax, edx
    ja .missing
    cmp ecx, 28
    jb .missing
    test dword [esi+48], 1
    jz .commit
    mov eax, [ebp-8]
    mov dword [ebx+scratch_path+eax-4], '.AI'
    push 0x200
    lea eax, [ebx+scratch_path]
    push eax
    call OPEN
    add esp, 8
    test eax, eax
    js .missing
    push eax
    call CLOSE
    add esp, 4
    mov eax, [ebp-8]
    mov dword [ebx+scratch_path+eax-4], '.REZ'
.commit:
    cmp dword [ebp-12], 0
    jl .base_only
    movzx eax, word [edi+0x9370]
    mov [ebp-20], eax
    lea eax, [ebx+scratch_path]
    push eax
    call 0x85e25 ; CToPString
    add esp, 4
    push eax
    call 0x8454a
    add esp, 4
    cmp ax, -1
    je .open_failed
    ; Open the replacement before closing the previous map. Fonts and other
    ; base resources remain in map zero. The new map is temporarily at 1 or 2.
    mov eax, [ebp-20]
    mov edx, [edi+0x14ac8+eax*4]
    mov [ebp-24], edx
    movzx edx, word [edi+0x14adc+eax*2]
    push edx
    call drop_overlay
    pop edx
    mov eax, [ebp-24]
    mov [edi+0x14acc], eax
    mov [edi+0x14ade], dx
    mov dword [edi+0x14ad0], 0
    mov word [edi+0x14ae0], 0
    mov word [edi+0x9370], 2
    mov dword [ebx+overlay], 1
    jmp .copy
.open_failed:
    ; OpenResFile leaves its count incremented on some error paths.
    mov eax, [ebp-20]
    mov word [edi+0x9370], ax
    mov dword [edi+0x14ac8+eax*4], 0
    mov word [edi+0x14adc+eax*2], 0
    jmp .missing
.base_only:
    call drop_overlay
.copy:
    push edi
    lea edi, [ebx+active]
    mov ecx, 16
    rep movsd
    pop edi
%ifdef GAME_PROFILES
    call commit_game_rules
%endif
%ifdef TERRAIN_RULES
    call commit_terrain_rules
%endif
    lea eax, [ebx+active+8]
    push eax
    lea eax, [ebx+ai_path]
    push eax
    call make_path
    add esp, 8
    mov eax, [ebp-8]
    mov dword [ebx+ai_path+eax-4], '.AI'
%ifdef PRESENTATION
    ; InitGameBits caches both nationality flag sheets. Reload those buffers
    ; after each successful selection/resume, including a return to base art.
    ; The first preview may run before InitGameBits has allocated the buffers.
    mov eax, [edi+0x7ccd]
    test eax, eax
    jz .art_done
    cmp dword [eax+0x40], 0
    je .flags_done
    cmp dword [eax+0x44], 0
    je .flags_done
    push dword 560
    push byte 16
    call 0x25327 ; LoadAPict(buffer index, resource number)
    add esp, 8
    push dword 561
    push byte 17
    call 0x25327
    add esp, 8
.flags_done:
%ifdef SUPPORT_ARTWORK
    mov eax, [edi+0x7ccd]
    cmp dword [eax+0x34], 0
    je .support_done
    push dword 131
    push byte 13
    call 0x25327 ; Support category buttons, kept at native origin.
    add esp, 8
.support_done:
%endif
    mov eax, [edi+0x7ccd]
    cmp dword [eax+0x2c], 0
    je .art_done
    call refresh_toolbar
.art_done:
%endif
    mov eax, 1
    jmp .restore
.missing:
    push byte 0
    lea eax, [ebx+missing_text]
    push eax
    call 0x24d73
    add esp, 8
    xor eax, eax
.restore:
    mov [ebp-16], eax
    mov word [edi+0x9372], 0
    movsx eax, word [ebp-4]
    push eax
    push byte 0
    call 0x86e4d
    add esp, 8
    mov eax, [ebp-16]
    leave_fn
.invalid:
    xor eax, eax
    leave_fn

%ifdef PRESENTATION
; InitTBarButts rebases this cached bitmap to screen coordinates. LoadAPict
; draws using resource coordinates, so temporarily restore a zero origin.
; Preserve the live world's origin and caller's port across menu/save changes.
refresh_toolbar:
    enter_fn 12
    mov eax, [edi+0x7ccd]
    mov esi, [eax+0x2c]
    movsx eax, word [esi+0x10]
    mov [ebp-8], eax
    movsx eax, word [esi+0x12]
    mov [ebp-12], eax
    lea eax, [ebp-4]
    push eax
    call 0x84207 ; GetPort
    add esp, 4
    push esi
    call 0x841f5 ; SetPort
    add esp, 4
    push byte 0
    push byte 0
    call 0x1239 ; SetOrigin
    add esp, 8
    push dword 251
    push byte 11
    call 0x25327
    add esp, 8
    push dword [ebp-8]
    push dword [ebp-12]
    call 0x1239
    add esp, 8
    push dword [ebp-4]
    call 0x841f5
    add esp, 4
    leave_fn
%endif

get_resource:
    enter_fn 0
    mov word [edi+0x9372], 0
    cmp dword [ebx+overlay], 0
    je .get
    cmp dword [ebp+0x14], 'TCIP' ; numeric resource tag 0x50494354
    jne .get
    mov eax, [ebp+0x18]
%ifdef CUSTOM_ARTWORK
    cmp eax, 12000
    jb .other_art
    cmp eax, 12255
    jbe .custom
.other_art:
%endif
%ifdef PRESENTATION
%ifdef SUPPORT_ARTWORK
    cmp eax, 131
    je .custom
%endif
    cmp eax, 251
    je .custom
    cmp eax, 560
    je .custom
    cmp eax, 561
    je .custom
    cmp eax, 730
    je .custom
    cmp eax, 731
    je .custom
    cmp eax, 780
    je .custom
    cmp eax, 781
    je .custom
    cmp eax, 1100
    jb .existing
    cmp eax, 1103
    jbe .custom
.existing:
%endif
    cmp eax, 128
    je .custom
    cmp eax, 138
    je .custom
    cmp eax, 144
    jb .get
    cmp eax, 151
    jbe .custom
    cmp eax, 300
    jb .get
    cmp eax, 311
    jbe .custom
    cmp eax, 4500
    jb .get
    cmp eax, 4606
    ja .get
.custom:
    mov word [edi+0x9372], 1
.get:
    push dword [ebp+0x18]
    push dword [ebp+0x14]
    call native_resource
    add esp, 8
    leave_fn

; LoadGame's RWScenario call: discover save identity before any unit/terrain
; artwork is rebuilt. The SCN/SAV block layout remains entirely native.
load_identity:
    enter_fn 0
    push dword [ebp+0x1c]
    push dword [ebp+0x18]
    push dword [ebp+0x14]
    call 0x28d85
    add esp, 12
    cmp byte [edi+0x8047], 0
%ifdef ADVANCED_ORDERS
    je .resume
    call events_initialize
    test eax, eax
    jz .events_bad
    jmp .done
.resume:
%else
    jne .done ; fresh start already has the selected identity
%endif
    lea eax, [ebx+resume_record]
    push eax
    push dword [ebp+0x18]
    call peek_footer
    add esp, 8
    test eax, eax
    jnz .activate
%ifdef TERRAIN_RULES
    cmp dword [ebx+resume_record], 'WAWL'
    je .fatal
%endif
    mov eax, [edi+0x7d5f]
    movzx eax, byte [eax+0x1220]
    cmp eax, 6
    ja .fatal
    imul eax, 13
    lea eax, [ebx+native_names+eax]
    push eax
    lea eax, [ebx+resume_record]
    push eax
    call default_record
    add esp, 8
.activate:
    lea eax, [ebx+resume_record]
    push eax
    call activate_assets
    add esp, 4
    test eax, eax
    jz .fatal
%ifdef ADVANCED_ORDERS
    call events_initialize
    test eax, eax
    jz .events_bad
    push dword [ebp+0x18]
    call events_restore
    add esp, 4
    test eax, eax
    jz .events_bad
%endif
    ; Find the saved scenario in the discovery list, if still installed.
    call scan
    xor esi, esi
.find:
    cmp esi, [ebx+state_count]
    jae .unknown
    mov eax, esi
    shl eax, 6
    lea eax, [ebx+records+eax+8]
    push eax
    lea eax, [ebx+active+8]
    push eax
    call 0x8cc22
    add esp, 8
    test eax, eax
    jz .found
    inc esi
    jmp .find
.unknown:
    mov esi, -1
.found:
    mov [ebx+state_selected], esi
    cmp esi, -1
    je .bounds
    mov eax, esi
    xor edx, edx
    mov ecx, 5
    div ecx
    sub esi, edx
    mov [ebx+state_page], esi
.bounds:
    call preview_bounds
.done:
    leave_fn
%ifdef ADVANCED_ORDERS
.events_bad:
    push byte 1
    lea eax, [ebx+events_error]
    push eax
    call 0x24d73
    add esp, 8
    call 0x86288
%endif
.fatal:
    push byte 1
    lea eax, [ebx+resume_error]
    push eax
    call 0x24d73
    add esp, 8
    call 0x86288

save_identity:
    enter_fn 0
    cmp dword [ebx+active], 'WAWL'
    jne .close
%ifdef ADVANCED_ORDERS
    cmp dword [ebx+event_key], 'WAWA'
    jne .identity
    push byte 80
    push dword [ebp+0x14]
    lea eax, [ebx+event_state]
    push eax
    call 0x27215
    add esp, 12
.identity:
%endif
    push byte 64
    push dword [ebp+0x14]
    lea eax, [ebx+active]
    push eax
    call 0x27215 ; checked WriteToFile(buffer, fd, count)
    add esp, 12
%ifdef NESTED_EVENTS
    ; Native repeated saves overwrite without truncating. Orders can shrink
    ; the file, leaving a stale identity/event footer beyond the new end.
    ; DOS binary write(count=0) truncates at the current file position.
    push byte 0
    lea eax,[ebx+active]
    push eax
    push dword [ebp+0x14]
    call 0x8f643
    add esp,12
    test eax,eax
    jnz nested_failure
%endif
.close:
    push dword [ebp+0x14]
    call 0x869d9
    add esp, 4
    leave_fn
open_orders:
    enter_fn 0
    mov eax, [ebp+0x14]
    cmp dword [ebx+active], 'WAWL'
    jne .open
    lea eax, [ebx+ai_path]
.open:
    push dword [ebp+0x18]
    push eax
    call OPEN
    add esp, 8
    leave_fn

preview_bounds:
    mov eax, [edi+0x7d5f]
    test dword [ebx+active+48], 1
    jz .native
    mov dx, [eax+0x22a]
    inc dx
    mov [edi+0x7773], dx
    mov dx, [eax+0x228]
    inc dx
    mov [edi+0x7771], dx
    ret
.native:
    mov edx, [cs:ebx+native_dimensions]
    mov [edi+0x7771], edx
    ret

native_read:
    push ebx
    push esi
    push edi
    push ebp
    mov ebp, esp
    jmp 0x26f58
native_secondary:
    push ebx
    push esi
    push edi
    push ebp
    mov ebp, esp
    jmp 0x3ee7c
native_resource:
    push ebx
    push esi
    enter 8, 0
    jmp 0x84875

%ifdef CUSTOM_ARTWORK
; DrawLeaderSideBar's final ResetPenColor call. Optional 37x35 portrait in
; the nationality-flag area, below the combat ratings. Keep chit and controls.
leader_portrait:
    enter_fn 24
    call 0x251e9
    movzx eax, byte [edi+0x8037]
    cmp eax, 1
    ja .done
    mov ecx, [edi+0x7d5f]
    test ecx, ecx
    jz .done
    movzx edx, byte [edi+eax+0x6f54]
    cmp dl, byte [ecx+eax+0x3a2]
    jae .done
    mov ecx, [edi+eax*4+0x7d03]
    imul edx, 36
    add ecx, edx
    mov [ebp-24], ecx
    cmp dword [ebx+portrait_drawn], 0
    je .lookup
    ; Restore the flag area before drawing another portrait or retaining the
    ; new leader's flag. Native transparent blits do not erase old pixels.
    movsx eax, word [edi+0x1159c]
    add eax, 123
    mov [ebp-12], ax
    add eax, 35
    mov [ebp-8], ax
    movsx eax, word [edi+0x1159e]
    add eax, 4
    mov [ebp-10], ax
    add eax, 37
    mov [ebp-6], ax
    lea eax, [edi+0xf196]
    push eax
    lea eax, [ebp-12]
    push eax
    call 0x250cd
    add esp, 8
    mov ecx, [ebp-24]
    movzx eax, byte [ecx+30]
    movsx ecx, word [edi+0xf1ac]
    imul eax, ecx
    mov edx, [edi+0xf1bb]
    mov [ebp-20], edx
    mov edx, [edi+0xf1bf]
    mov [ebp-16], edx
    push byte 0
    push eax
    lea eax, [ebp-20]
    push eax
    call 0x80dd5
    add esp, 12
    push byte 0
    push byte 8
    lea eax, [edi+0x11614]
    push eax
    lea eax, [ebp-20]
    push eax
    push byte 6
    push byte 16
    call 0x250f9
    add esp, 24
    mov dword [ebx+portrait_drawn], 0
.lookup:
    cmp dword [ebx+overlay], 0
    je .done
    movzx eax, byte [edi+0x8037]       ; PMode (displayed side)
    cmp eax, 1
    ja .done
    mov ecx, [edi+0x7d5f]
    test ecx, ecx
    jz .done
    movzx edx, byte [edi+eax+0x6f54] ; CurrentLeader[side]
    cmp dl, byte [ecx+eax+0x3a2]
    jae .done
    shl eax, 7
    lea esi, [eax+edx+12000]
    movzx eax, word [edi+0x9372]
    mov [ebp-4], eax
    mov word [edi+0x9372], 1
    ; Probe without GetResource's missing-resource alert. Old exports and
    ; leaders without an assigned portrait keep their existing sidebar.
    push esi
    push dword 'TCIP'
    call 0x8537b
    add esp, 8
    test eax, eax
    jz .restore
    movsx eax, word [edi+0x1159c]    ; SBRect.top
    add eax, 123
    push eax
    movsx eax, word [edi+0x1159e]    ; SBRect.left
    add eax, 4
    push eax
    push byte 6                      ; sidebar port
    push esi
    call 0x2528a                     ; GetDrawDispose(id, port, x, y)
    add esp, 16
    mov dword [ebx+portrait_drawn], 1
.restore:
    mov eax, [ebp-4]
    mov [edi+0x9372], ax
.done:
    leave_fn
portrait_drawn: dd 0
%endif

%ifdef ADVANCED_ORDERS
%include 'game/waw/patches/dday-advanced-orders.asm'
%ifdef NESTED_EVENTS
%include 'game/waw/patches/dday-nested-events.asm'
%endif
%endif

%ifdef GAME_PROFILES
%include 'game/waw/patches/dday-game-profiles.asm'
%ifdef TERRAIN_RULES
%include 'game/waw/patches/dday-terrain-rules.asm'
%endif
%endif

%ifdef STARTUP_SELECTION
%include 'game/waw/patches/dday-startup-selection.asm'
%endif

folder: db 'SCENARIO',92,0
pattern: db 'SCENARIO',92,'*.SCN',0
previous_text: db '< Previous',0
next_text: db 'Next >',0
empty_text: db 0
missing_text: db 'Missing or invalid scenario REZ/AI. Export all three files together.',0
empty_library_text: db 'No playable D-Day scenarios found in SCENARIO. Install SCN/REZ/AI exports there.',0
full_text: db 'Scenario limit reached: only the first 256 files are listed.',0
resume_error: db 'Cannot resume: install this saved scenario',39,'s matching REZ and AI in SCENARIO.',0
%ifndef SOURCE_EXE
%define SOURCE_EXE 'game/waw/dday/orig/INVADE.EXE'
%endif
native_titles: incbin SOURCE_EXE,0x10eddd,182
native_names: incbin SOURCE_EXE,0x10ee93,91
native_dimensions: incbin SOURCE_EXE,0x10edc5,4
align 4
scanned: dd 0
state_count: dd 0
state_selected: dd -1
state_page: dd 0
overlay: dd 0
active: times 64 db 0
resume_record: times 64 db 0
ai_path: times 32 db 0
rez_header: times 16 db 0
scratch_path: times 32 db 0
scratch_header: times 0x1262 db 0
align 4
identifiers: times LIMIT db 0
records: times LIMIT*RECORD db 0
code_end:
