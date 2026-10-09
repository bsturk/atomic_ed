; WAWAI004: nested ALL/ANY expressions, held HQ reinforcements and public
; one-shot messages. Reuses the fingerprinted 80-byte saved activation state.
%define NROW 320

nested_read_row: ; cdecl(fd,buffer320); guards and compact to 282 logical bytes
    enter_fn 0
    push dword NROW
    push dword [ebp+0x18]
    push dword [ebp+0x14]
    call READ
    add esp,12
    cmp eax,NROW
    jne .bad
    mov esi,[ebp+0x18]
    add esi,16
    mov edi,esi
    mov edx,19
.chunk:
    cmp word [esi],0xffff
    jne .bad
    add esi,2
    mov ecx,14
    rep movsb
    dec edx
    jnz .chunk
    mov eax,1
    leave_fn
.bad:
    or eax,-1
    leave_fn

nested_conditions: ; cdecl(logical row,scenario,evaluate), 1/0 or -1 malformed
    enter_fn 80 ; bool stack 64, stack count -68, token index -72, scratch -76/80
    mov esi,[ebp+0x14]
    mov edx,[ebp+0x18]
    mov al,[esi+1]
    and al,0xfe
    cmp al,0x84
    jne .bad
    mov al,[edx+0x1220]
    cmp al,[esi]
    jne .bad
    cmp word [esi+2],1
    ja .bad
    cmp byte [esi+16],2
    ja .bad
    cmp byte [esi+17],32
    ja .bad
    cmp byte [esi+18],1
    ja .bad
    cmp byte [esi+16],1
    je .header
    cmp byte [esi+18],0
    jne .bad
.header:
    cmp byte [esi+19],0
    jne .bad
    cmp dword [esi+20],0
    jne .bad
    cmp dword [esi+24],0
    jne .bad
    cmp word [esi+280],0
    jne .bad
    ; Additive row checksum excludes its own four-byte field.
    xor eax,eax
    xor ecx,ecx
.sum:
    cmp ecx,28
    jne .byte
    add ecx,4
.byte:
    movzx ebx,byte [esi+ecx]
    add eax,ebx
    inc ecx
    cmp ecx,282
    jb .sum
    cmp eax,[esi+28]
    jne .bad
    call bases
    mov edx,[ebp+0x18]
    cmp word [esi+6],1
    jb .bad
    movzx eax,word [esi+8]
    cmp ax,[esi+6]
    jb .bad
    mov ecx,[edx+0x48]
    sub ecx,[edx+0x44]
    inc ecx
    cmp eax,ecx
    ja .bad
    cmp byte [esi+16],2
    je .message_group
    movzx eax,word [esi+2]
    movzx ecx,word [esi+4]
    cmp cx,[edx+0x23c+eax*2]
    jae .bad
    jmp .order
.message_group:
    cmp word [esi+4],0xffff
    jne .bad
.order:
    cmp byte [esi+16],0
    jne .action
    mov ax,[esi+10]
    cmp ax,1
    je .goal
    cmp ax,3
    je .goal
    sub ax,6
    cmp ax,2
    ja .bad
.goal:
    mov ax,[esi+12]
    cmp ax,[edx+0x226]
    jl .bad
    cmp ax,[edx+0x22a]
    jge .bad
    mov ax,[esi+14]
    cmp ax,[edx+0x224]
    jl .bad
    cmp ax,[edx+0x228]
    jge .bad
    jmp .text
.action:
    cmp byte [esi+1],0x84 ; one-shot actions cannot be latched orders
    jne .bad
    cmp word [esi+10],7
    jne .bad
.text:
    xor ecx,ecx
    xor edx,edx
.text_byte:
    movzx eax,byte [esi+160+ecx]
    cmp byte [esi+16],2
    jne .zero
    test edx,edx
    jnz .zero
    test eax,eax
    jnz .printable
    test ecx,ecx
    jz .bad
    inc edx
    jmp .text_next
.printable:
    cmp eax,32
    jb .bad
    cmp eax,127
    je .bad
    cmp ecx,119
    je .bad
    jmp .text_next
.zero:
    test eax,eax
    jnz .bad
.text_next:
    inc ecx
    cmp ecx,120
    jb .text_byte
    ; Unused token slots must be zero, too.
    movzx ecx,byte [esi+17]
.padding:
    cmp ecx,32
    jae .evaluate
    cmp dword [esi+32+ecx*4],0
    jne .bad
    inc ecx
    jmp .padding
.evaluate:
    mov dword [ebp-68],0
    mov dword [ebp-72],0
.token:
    mov ecx,[ebp-72]
    cmp cl,[esi+17]
    jae .result
    mov eax,[esi+32+ecx*4]
    mov [ebp-76],eax
    cmp al,16
    je .combine
    cmp al,17
    je .combine
    cmp al,1
    je .objective
    cmp al,2
    jne .bad
    cmp ah,1
    ja .bad
    shr eax,16
    test eax,eax
    jz .bad
    mov edx,1
    cmp dword [ebp+0x1c],0
    je .push
    imul ecx,eax,1000
    movzx eax,byte [ebp-75]
    xor eax,1
    imul eax,824
    mov edx,[edi+0x7d57]
    test edx,edx
    jz .bad
    cmp [edx+eax+20],ecx
    setae dl
    movzx edx,dl
    jmp .push
.objective:
    cmp ah,1
    ja .bad
    shr eax,16
    mov edx,[ebp+0x18]
    movzx edx,byte [edx+0x1222]
    cmp eax,edx
    jae .bad
    mov edx,1
    cmp dword [ebp+0x1c],0
    je .push
    imul eax,48
    mov edx,[edi+0x7d53]
    test edx,edx
    jz .bad
    mov cl,[ebp-75]
    cmp cl,[edx+eax+17]
    sete dl
    movzx edx,dl
.push:
    mov ecx,[ebp-68]
    cmp ecx,16
    jae .bad
    mov [ebp-64+ecx*4],edx
    inc dword [ebp-68]
    jmp .next
.combine:
    test eax,0xffff0000
    jnz .bad
    movzx ecx,ah
    test ecx,ecx
    jz .bad
    cmp ecx,[ebp-68]
    ja .bad
    xor edx,edx
    cmp al,16
    sete dl
    mov [ebp-80],ecx
.reduce:
    dec dword [ebp-68]
    mov ecx,[ebp-68]
    cmp byte [ebp-76],16
    jne .or
    and edx,[ebp-64+ecx*4]
    jmp .reduced
.or:
    or edx,[ebp-64+ecx*4]
.reduced:
    dec dword [ebp-80]
    jnz .reduce
    jmp .push
.next:
    inc dword [ebp-72]
    jmp .token
.result:
    mov eax,1
    cmp byte [esi+17],0
    je .done
    cmp dword [ebp-68],1
    jne .bad
    mov eax,[ebp-64]
.done:
    leave_fn
.bad:
    or eax,-1
    leave_fn

nested_release: ; cdecl(row,hold); future ground members of one HQ, incl HQ itself
    enter_fn 0
    mov esi,[ebp+0x14]
    movzx ecx,word [esi+2]
    mov eax,[edi+0x7d5f]
    movzx edx,word [eax+0x244+ecx*2]
    mov ebx,[edi+0x7cf3+ecx*4]
    mov edi,[edi+0x7d63]
    mov edi,[edi+12]
    cmp dword [ebp+0x18],0
    je .target
    mov eax,[eax+0x48]
    inc eax
    jmp .loop
.target:
    mov eax,edi ; next normal arrival phase sees date == calendar-1
.loop:
    test edx,edx
    jz .done
    cmp byte [ebx+0x76],5
    je .next
    cmp byte [ebx+0x76],6
    je .next
    cmp [ebx+8],edi
    jl .next ; deployed and deleted units are never revived/rescheduled
    movzx ecx,byte [ebx+0x81]
    cmp byte [ebx+0x76],7
    jne .group
    mov ecx,[ebx+4]
.group:
    cmp cx,[esi+4]
    jne .next
    mov [ebx+8],eax
.next:
    add ebx,172
    dec edx
    jmp .loop
.done:
    leave_fn

nested_process: ; cdecl(mode,unit,original_bg_frame): 0 validate,1 hold,2 tick,3 order
    enter_fn 400
    mov dword [ebp-16],0 ; row index
    mov dword [ebp-20],1 ; result
    lea eax,[ebp-4]
    call home_volume
    push 0x200
    lea eax,[ebx+events_default_path]
    push eax
    call open_orders
    add esp,8
    mov [ebp-8],eax
    test eax,eax
    js .bad_volume
    lea ecx,[ebp-384]
    push ecx
    push eax
    call events_read_header
    add esp,8
    cmp eax,1
    jne .bad
    cmp dword [ebp-380],'I004'
    jne .bad
    xor ecx,ecx
.key:
    mov eax,[ebp-384+ecx]
    cmp eax,[ebx+event_key+ecx]
    jne .bad
    add ecx,4
    cmp ecx,32
    jb .key
    movzx eax,word [ebp-376]
    mov [ebp-12],eax
.row:
    lea esi,[ebp-352]
    push esi
    push dword [ebp-8]
    call nested_read_row
    add esp,8
    test eax,eax
    js .bad
    push byte 0
    push dword [edi+0x7d5f]
    push esi
    call nested_conditions
    add esp,12
    test eax,eax
    js .bad
    cmp dword [ebp+0x14],0
    je .next
    cmp dword [ebp+0x14],1
    jne .active
    cmp byte [esi+16],1
    jne .next
    cmp byte [esi+18],1
    jne .next
    push byte 1
    push esi
    call nested_release
    add esp,8
    jmp .next
.active:
    mov eax,[edi+0x7d63]
    mov eax,[eax+12]
    mov edx,[edi+0x7d5f]
    sub eax,[edx+0x44]
    inc eax
    movzx ecx,word [esi+6]
    cmp eax,ecx
    jl .next
    movzx ecx,word [esi+8]
    cmp eax,ecx
    jg .next
    cmp dword [ebp+0x14],3
    je .order_test
    cmp byte [esi+16],0
    je .next
    mov ecx,[ebp-16]
    bt [ebx+event_bits],ecx
    jc .next
    jmp .condition
.order_test:
    cmp byte [esi+16],0
    jne .next
    mov eax,[ebp+0x18]
    mov cl,[eax+0x74]
    cmp cl,[esi+2]
    jne .next
    mov cl,[eax+0x81]
    cmp cl,[esi+4]
    jne .next
.condition:
    push byte 1
    push edx
    push esi
    call nested_conditions
    add esp,12
    test eax,eax
    js .bad
    jnz .apply
    cmp byte [esi+1],0x85
    jne .next
    mov ecx,[ebp-16]
    bt [ebx+event_bits],ecx
    jnc .next
.apply:
    cmp byte [esi+16],0
    jne .once
    cmp byte [esi+1],0x85
    jne .outputs
    mov ecx,[ebp-16]
    bts [ebx+event_bits],ecx
.outputs:
    mov ecx,[ebp+0x1c]
    mov ax,[esi+10]
    mov edx,[ecx+0x18]
    mov [edx],ax
    mov edx,[ecx+0x1c]
    mov [edx],ax
    mov ax,[esi+12]
    mov edx,[ecx+0x20]
    mov [edx],ax
    mov ax,[esi+14]
    mov edx,[ecx+0x24]
    mov [edx],ax
    jmp .close
.once:
    mov ecx,[ebp-16]
    bts [ebx+event_bits],ecx
    cmp byte [esi+16],1
    jne .message
    push byte 0
    push esi
    call nested_release
    add esp,8
    jmp .next
.message:
    lea eax,[esi+160]
    push eax
    call nested_message
    add esp,4
.next:
    inc dword [ebp-16]
    mov eax,[ebp-16]
    cmp eax,[ebp-12]
    jb .row
    jmp .close
.bad:
    mov dword [ebp-20],-1
.close:
    push dword [ebp-8]
    call CLOSE
    add esp,4
    jmp .volume
.bad_volume:
    mov dword [ebp-20],-1
.volume:
    movsx eax,word [ebp-4]
    push eax
    push byte 0
    call 0x86e4d
    add esp,8
    mov eax,[ebp-20]
    leave_fn

nested_run_checked: ; mode EAX; EBX/EDI bases, used by start/turn wrappers
    cmp dword [ebx+event_key+4],'I004'
    jne .done
    push byte 0
    push byte 0
    push eax
    call nested_process
    add esp,12
    test eax,eax
    js nested_failure
.done:
    ret
nested_failure:
    push byte 1
    lea eax,[ebx+events_error]
    push eax
    call 0x24d73
    add esp,8
    call 0x86288

nested_start: ; StartAGame's RestoreCursor call, after initial maps/UI are ready
    enter_fn 0
    call 0x4a475
    cmp byte [edi+0x8047],0
    je .done
    mov eax,1
    call nested_run_checked
    mov eax,2
    call nested_run_checked
.done:
    leave_fn

nested_turn: ; after normal objective ownership/scoring update, before end-game check
    enter_fn 0
    call 0x52e78 ; TabulateCities
    mov eax,2
    call nested_run_checked
    leave_fn

nested_orders:
    pushad
    push ebp
    push dword [ebp+0x14]
    push byte 3
    call nested_process
    add esp,12
    test eax,eax
    jns .done
    call bases
    call nested_failure
.done:
    popad
    mov esp,ebp
    pop ebp
    pop edi
    pop esi
    jmp 0x67b5a

; Reuse the native portrait/help panel and its click-to-dismiss loop. Negative
; help ID -6 always displays, even when player hints are disabled. The drawing
; callback wraps to measured font widths, continuing on another page if needed.
; Existing debug/error dialogs continue through the original WriteDebugMsg.
nested_message: ; cdecl(C string)
    enter_fn 4
    movzx eax,byte [edi+0x7e1e]
    mov [ebp-4],eax
    mov eax,[ebp+0x14]
    mov [ebx+nested_message_cursor],eax
.page:
    mov byte [edi+0x7e1e],1
    push byte 1
    push byte 0
    push byte -6
    push dword [edi+0x12a1c]
    call 0x1f0c0 ; ShowHelp(point,id,wait mode,portrait)
    add esp,16
    mov eax,[ebx+nested_message_cursor]
    cmp byte [eax],0
    jne .page
    mov eax,[ebp-4]
    mov [edi+0x7e1e],al
    mov dword [ebx+nested_message_cursor],0
    leave_fn

nested_draw_message: ; WriteMsgToHelp's WriteDebugMsg call site
    cmp word [esp+4],-6
    jne 0x1f64f
    enter_fn 144 ; line buffer120; line count -124, width -128, last space -132
    push byte 1
    push byte 0
    lea eax,[ebx+nested_message_title]
    push eax
    call 0x1f701 ; PrintOneLine(C string,y,face)
    add esp,12
    push byte 0
    call 0x83e84 ; TextFace: body measurements use plain face
    add esp,4
    mov dword [ebp-124],0
.line:
    mov esi,[ebx+nested_message_cursor]
.skip:
    cmp byte [esi],' '
    jne .begin
    inc esi
    jmp .skip
.begin:
    mov [ebx+nested_message_cursor],esi
    cmp byte [esi],0
    je .footer
    mov [ebp-136],esi ; line start
    mov dword [ebp-128],0
    mov dword [ebp-132],0
.measure:
    movzx eax,byte [esi]
    test eax,eax
    jz .copy
    push eax
    call 0x83f3b ; CharWidth with active 9-point font
    add esp,4
    movsx eax,ax
    add [ebp-128],eax
    cmp dword [ebp-128],132
    jbe .fits
    cmp dword [ebp-132],0
    je .copy
    mov esi,[ebp-132]
    jmp .copy
.fits:
    cmp byte [esi],' '
    jne .advance
    mov [ebp-132],esi
.advance:
    inc esi
    jmp .measure
.copy:
    mov [ebx+nested_message_cursor],esi
    mov ecx,esi
    mov esi,[ebp-136]
    sub ecx,esi
    lea edi,[ebp-120]
    rep movsb
    mov byte [edi],0
    push byte 0
    imul eax,[ebp-124],10
    add eax,14
    push eax
    lea eax,[ebp-120]
    push eax
    call 0x1f701
    add esp,12
    inc dword [ebp-124]
    cmp dword [ebp-124],3
    jb .line
.footer:
    lea eax,[ebx+nested_message_close]
    mov esi,[ebx+nested_message_cursor]
    cmp byte [esi],0
    je .footer_draw
    lea eax,[ebx+nested_message_more]
.footer_draw:
    push byte 0
    push byte 46
    push eax
    call 0x1f701
    add esp,12
    leave_fn

nested_message_cursor: dd 0
nested_message_title: db 'Scenario update',0
nested_message_close: db 'Click to close',0
nested_message_more: db 'Click for more',0
