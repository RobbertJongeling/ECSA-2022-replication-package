# ECSA-2022-replication-package


## Abstract
This repository contains the code and demos to support our ECSA-2022 submission "From informal architecture diagrams to flexible blended models".

In the paper, we show how we can make more use of informal diagrams by considering them, partly, as models. We show how to migrate from just informal diagrams to flexible models, by providing a textual grammar for the elements of the diagram that shall be considered model elements. Moreover, we show how we can continue the blended use of the pre-existing informal diagram and the newly derived textual model, by means of two unidirectional transformations that synchronize the representations. Crucially, we preserve the layout of the informal diagrams as well as all the "non-modeling" elements in it.

The figure below provides an overview of the approach
![modelingwithdrawio drawio](https://user-images.githubusercontent.com/4225829/167256190-05a65831-53dc-4f1f-844b-cc7fc2afd35e.png)


## Demo videos
To better illustrate the approach and its implementation, we provide three demo video's that show the synchronization and several supported features. __Demo3__ (7 mins) contains the most functionality.


## Contents
This repository shows the following three demo scenarios. For each of them we provide code and a demo video in this repository.

  1. arch-demo-industry-eval: This folder contains the supporting code for the demo with a simple architecture diagram, as used for the industrial evaluation in the paper.
  2. state-machine-blended-demo: This folder contains the supporting code for the demo with a state machine diagram, to show that the approach can handle connectors/edges too, in addition to boxes/nodes.
  3. arch-demo: This folder contains the supporting code for the demo with an extended architecture diagram, as described in the paper. This demo shows that the approach can in addition to the previous two demo's, also handle "containments" of elements in other elements.
