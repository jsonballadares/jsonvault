status:: #fleeting
tags:: #programming, #concept

---
# Go Strings Bytes and Runes

![[Screenshot 2026-01-18 at 4.06.48 PM.png]]
![[Screenshot 2026-01-18 at 4.06.37 PM.png]]
![[Screenshot 2026-01-18 at 4.07.07 PM.png]]
![[Screenshot 2026-01-18 at 4.07.36 PM.png]]
![[Screenshot 2026-01-18 at 4.08.14 PM.png]]
![[Screenshot 2026-01-18 at 4.08.31 PM.png]]
![[Screenshot 2026-01-18 at 4.10.34 PM.png]]

When you're dealing with strings in Go you're dealing with a value whose underlying representation is an array of bytes. This is why when you take the length of a string it is the number of bytes, not the number of characters (runes).

![[Screenshot 2026-01-18 at 4.14.37 PM.png]]

The `rune` type is fundamentally a 32-bit integer, allowing it to store the wide range of values needed to represent any Unicode character (up to 0x10FFFF). A Unicode code point is a unique number assigned to every character in virtually all the world's writing systems, symbols, and emojis.

![[Screenshot 2026-01-18 at 4.43.23 PM.png]]
![[Screenshot 2026-01-18 at 4.44.10 PM.png]]
![[Screenshot 2026-01-18 at 4.45.03 PM.png]]
![[Screenshot 2026-01-18 at 4.45.23 PM.png]]
![[Screenshot 2026-01-18 at 4.45.41 PM.png]]
![[Screenshot 2026-01-18 at 4.47.54 PM.png]]
![[Screenshot 2026-01-18 at 4.58.39 PM.png]]

---
# References

- [[Go]]
