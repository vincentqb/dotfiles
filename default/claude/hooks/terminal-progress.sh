#!/bin/sh
# Declare busy (OSC 9;4;3) or idle (OSC 9;4;0) on the terminal of the nearest ancestor that has one.
case "$1" in busy) s=3 ;; *) s=0 ;; esac
p=$PPID
while [ "${p:-1}" -gt 1 ]; do
  t=$(ps -o tty= -p "$p" 2>/dev/null | tr -d ' ')
  case "$t" in pts/*|tty*) printf '\033]9;4;%s;\007' "$s" > "/dev/$t" 2>/dev/null; exit 0 ;; esac
  p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
done
exit 0
