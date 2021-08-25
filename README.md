# GrampsCrossing

This utility is intended to optimise the layout of a relationship graph produced with Gramps (genealogy software https://github.com/gramps-project/gramps).

The relationship graph uses graphviz to produce charts. For large or complex graphs, the layout is sometimes not optimised well and can result in many crossed lines. However, the layout is somewhat sensitive to the order of the input data. This utility iterates the order of individual items in the input file to minimise the number of crossings in the output chart.

Usage: 

    create a relationship graph in Gramps to produce .gv file 
    
    copy the .gv file and this .py file to the same directory 
    
    in that directory, run 
    
      $./GrampsCrossing.py yourfile.gv 
      
    it takes several minutes, depending on file size 
    
    it doesn't alter your .gv file 
    
    it saves optimised files as .dot and .pdf files 
    
    ctrl c stops iterations and dumps current .dot and .pdf
