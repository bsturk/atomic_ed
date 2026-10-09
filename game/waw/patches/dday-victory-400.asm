; Expand victory history to 400 turns while reading native 260-turn records.
; Reuse SwapVictory/RWVictory's space, retaining all five LE relocation cells
; at their original addresses. The DOS loader never called SwapVictory.
BITS 32
ORG 0x27770

start:
    push ebx
    push esi
    push edi
    push ebp
    mov ebp, esp
    sub esp, 4
    call .pc
.pc:
    pop ebx
    sub ebx, .pc
    mov edi, [cs:ebx+0x27867]  ; relocated address of Victory pointer
    movsx esi, word [ebp+0x14]
    cmp word [ebp+0x18], 0
    jne write
    push esi
    call 0x2732b              ; ReadLong
    add esp, 4
    mov [ebp-4], eax
    cmp eax, 1088
    je .valid
    cmp eax, 1648
    jne bad
.valid:
    push dword 1648
    push edi
    call 0x25014              ; NewPtr
    add esp, 8
    push edi
    mov edi, [edi]
    xor eax, eax
    mov ecx, 412
    cld
    rep stosd
    pop edi
    push dword [ebp-4]
    push esi
    push dword [edi]
    call 0x271a2              ; ReadFromFile
    add esp, 12
    cmp dword [ebp-4], 1648
    je done
    jmp expand

times 0x27808-($-$$+0x27770) db 0x90
rw_victory:
    jmp start
expand:
    mov edx, [edi]
    lea esi, [edx+1084]
    lea edi, [edx+1364]
    mov ecx, 136
    std
    rep movsd                ; move Axis record backward, safe for overlap
    cld
    lea edi, [edx+544]
    xor eax, eax
    mov ecx, 70
    rep stosd                ; zero newly available Allied history
    jmp done

; LE loader writes these operands even though they are now unused data.
times 0x27856-($-$$+0x27770) db 0x90
dd 0x16b6
times 0x27867-($-$$+0x27770) db 0x90
dd 0x7d57
times 0x2787e-($-$$+0x27770) db 0x90
dd 0x7d57
times 0x278a4-($-$$+0x27770) db 0x90
dd 0x7d57
times 0x278d1-($-$$+0x27770) db 0x90
dd 0x7d57

write:
    push esi
    push dword 1648
    call 0x27381              ; WriteLong
    add esp, 8
    push dword 1648
    push esi
    push dword [edi]
    call 0x27215              ; WriteToFile
    add esp, 12
done:
    mov esp, ebp
    pop ebp
    pop edi
    pop esi
    pop ebx
    ret
bad:
    push dword 1
    push dword [cs:ebx+0x27856]
    call 0x24d73              ; original "Victory size" error
    add esp, 8
    call 0x86288              ; ExitToShell if the error dialog returns
    jmp done
times 0x27929-($-$$+0x27770) db 0x90
