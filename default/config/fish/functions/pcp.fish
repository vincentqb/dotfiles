function pcp --wraps='rsync -ahrz --info=progress2' --description 'alias pcp=rsync -ahrz --info=progress2'
  rsync -ahrz --info=progress2 $argv
        
end
