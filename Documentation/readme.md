# Tools and test data

The test ontology was created using the visual language [GRAPHOL](https://www.diag.uniroma1.it/degiacom/papers/2022/fi2022lssd.pdf) that implements all of OWL2.

Many, but not all features available in OWL2-RL were used in our test sample. Hence the transformation rules inventory is not complete yet, although probably sufficient in 99% of cases.

The graphic editor for GRAPHOL is [EDDY 3.7.1](https://github.com/obdasystems/eddy/releases). It allows to compose ontologies, import existing ones, check the syntax, consistency and coherence of the result, and export the result to the usual formats (RDF/XML, Turtle, ...) as well as diagrams (PDF, PNG...).

Highly recommended!

# Advanced usage

OntoJSON is being used for generating JSON schemas corresponding to a railway telematics ontology; see [the CDM-Telematics repo](https://github.com/UICrail/CDM-Telematics).

The ontology developed there makes an extensive use of OWL2 restrictions, which resulted in important evolutions of the present software.
