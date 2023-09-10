function ssa --wraps='AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M 0' --description 'alias ssa=AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M 0'
  AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M 0 $argv
        
end
