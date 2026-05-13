# Neighbor-joining tree from distance matrix

from subprocess import call
from fatoolsng.lib.utils import random_string


def plot_nj(distance_matrix, tmp_dir, fmt='pdf', label_callback=None,
            tree_type='fan', branch_coloring=True):
    """ NJ uses R's ape library
        R will be called as a separate process instead as a embedded library
        in order to utilize paralel processing in multiple processor
    """

    # create matrix distance & color distance

    # raise RuntimeError

    file_id = random_string(3)

    matrix_file = f'{tmp_dir}/matrix-distance-{file_id}.txt'
    colors_file = f'{tmp_dir}/colors-distance-{file_id}.txt'
    script_file = f'{tmp_dir}/njtree-{file_id}.r'
    njtree_file = f'{tmp_dir}/njtree-{file_id}.{fmt}'
    label_file = f'{tmp_dir}/labels-{file_id}.txt'

    with open(matrix_file, 'w') as out_m, open(colors_file, 'w') as out_c:

        out_m.write('\t'.join(str(x) for x in distance_matrix.sample_ids))
        out_m.write('\n')
        for name, vals in zip(distance_matrix.sample_ids, distance_matrix.M):
            out_m.write(f'{name}\t' + '\t'.join(f'{x:2.3f}' for x in vals) + '\n')

        out_c.write('\n'.join(distance_matrix.C))
        out_c.write('\n')

    if label_callback:
        with open(label_file, 'w') as labelout:
            for sample_id in distance_matrix.sample_ids:
                labelout.write(f'{sample_id:d}\t{label_callback(sample_id)}\n')
        label_cmd = (f"L<-read.table('{label_file}',sep='\\t',header=F);"
                     "L[[1]]<-as.character(L[[1]]);"
                     "L[[2]]<-as.character(L[[2]]);"
                     "tree$tip.label<-L[[2]][tree$tip.label == L[[1]]]")
    else:
        label_cmd = ''

    if branch_coloring:
        edge_color_cmd = (
'''
tree <- reorder(tree, "postorder")
x = tree$edge[,2]
edge_colors <- ifelse(x > length(C), "###", C[x])
# traversing by postorder
for(i in 1:nrow(tree$edge)){
    if (edge_colors[i] == "###") {
        # get the color from previous mode
        nodes <- which(tree$edge[,1] == tree$edge[i,2])
        if(edge_colors[nodes[1]] == edge_colors[nodes[2]]) {
            edge_colors[i] <- edge_colors[nodes[1]]
        } else {
            edge_colors[i] <- "#474747"
        }
    }
}
'''
        )
    else:
        edge_color_cmd = '''edge_colors <- "#474747"'''

    with open(script_file, 'w') as scriptout:
        if fmt == 'pdf':
            cmd = f'pdf("{njtree_file}", width = 11.2, height=7)'
        elif fmt == 'png':
            cmd = f'png("{njtree_file}", width = 1024, height = 640)'
        legend_labels = ",".join(f'"{hs.label}"' for (hs,_,_) in distance_matrix.S)
        legend_colors = ",".join(f'"{hs.colour}"' for (hs,_,_) in distance_matrix.S)
        scriptout.write(f"""
library(ape)
M <- as.matrix( read.table("{matrix_file}", sep='\\t', header=T) )
C <- as.vector( read.table("{colors_file}", sep='\\t', header=F, comment.char = '')[,1] )
tree <- nj( M )
{edge_color_cmd}
{label_cmd}
{cmd}
plot(tree, "{tree_type}", tip.color=C,  edge.color=edge_colors, font=1, cex=0.7, label.offset=0.009)
legend('topright', inset=c(0,0), c({legend_labels}), col = c({legend_colors}), lty=1, cex=0.85, xpd=T)
""")

    ok = call(['Rscript', script_file])

    if ok != 0:
        raise RuntimeError("Rscript run unsucessfully")

    return njtree_file
