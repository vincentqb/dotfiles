function pcp --wraps='rsync -a --info=progress2' --description 'alias pcp=rsync -a --info=progress2'
  rsync -a --info=progress2 $argv
        
end
