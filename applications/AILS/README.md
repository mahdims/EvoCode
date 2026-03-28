![](https://camo.githubusercontent.com/1b8f04b8ff248ffd132c13343858d070c4805406bbd4c4651f9b27e9c2f01a58/68747470733a2f2f494e464f524d534a6f432e6769746875622e696f2f6c6f676f732f494e464f524d535f4a6f75726e616c5f6f6e5f436f6d707574696e675f4865616465722e6a7067) 
# AILS-II: An Adaptive Iterated Local Search Heuristic for the Large-scale Capacitated Vehicle Routing Problem

This archive is distributed in association with the [INFORMS Journal on Computing](https://pubsonline.informs.org/journal/ijoc) under the [MIT License](LICENSE).

The software and data in this repository are a snapshot of the software and data that were used in the research reported on in the paper AILS-II: An Adaptive Iterated Local Search Heuristic for the Large-Scale Capacitated Vehicle Routing Problem by V. R. Máximo, J. F. Cordeau and M. C. V. Nascimento. 

Important: This code is being developed on an on-going basis at [https://github.com/vinymax10/AILS-CVRP](https://github.com/vinymax10/AILS-CVRP). Please go there if you would like to get a more recent version or would like support

## Cite

To cite the contents of this repository, please cite this the paper and this repo, using their respective DOIs.

https://doi.org/10.1287/ijoc.2023.0106

https://doi.org/10.1287/ijoc.2023.0106.cd

Below is the BibTex for citing this snapshot of the repository.

```
@misc{Maximoetal2024,
  author =        {V. R. Máximo and J.-F.Courdeau and M. C. V. Nascimento},
  publisher =     {INFORMS Journal on Computing},
  title =         {AILS-II: An Adaptive Iterated Local Search Heuristic for the Large-scale Capacitated Routing Problem},
  year =          {2024},
  doi =           {10.1287/ijoc.2023.0106.cd},
  url =           {https://github.com/INFORMSJoC/2023.0106},
  note =          {Available for download at https://github.com/INFORMSJoC/2023.0106},
}  
```
## Other References

Besides citing the paper and this repo, those interested in using any part of this algorithm in academic works must cite the following references:

[1] Máximo, Vinícius R., Nascimento, Mariá C.V. (2021).
A hybrid adaptive iterated local search with diversification control to the capacitated vehicle routing problem. European Journal of Operational Research, Volume 294, p. 1108-1119, https://doi.org/10.1016/j.ejor.2021.02.024 (also available at [aXiv](https://arxiv.org/abs/2012.11021)).

[2] Máximo, Vinícius R., Cordeau, Jean-François, Nascimento, Mariá C.V. (2022).
An adaptive iterated local search heuristic for the Heterogeneous Fleet Vehicle Routing Problem. Computers & Operations Research, Volume 148, p. 105954.
https://doi.org/10.1016/j.cor.2022.105954 (also available at [aXiv](https://arxiv.org/abs/2111.12821)).

## Description

AILS-II is an Adaptive Iterated Local Search (AILS) meta-heuristic that embeds adaptive strategies to tune  diversity control parameters. These parameters are the perturbation degree and the acceptance criterion. They are key parameters to ensure that the method escapes from local optima and keeps an adequate level of exploitation and exploration of the method. Its implementation is in JAVA language.

## To run the algorithm

```console
java -jar AILSII.jar -file data/X-n214-k11.vrp -rounded true -best 10856 -limit 100 -stoppingCriterion Time 
```

Run the AILSII class that has the following parameters:

**-file** : the file address of the problem instance.

**-rounded** :  A flag that indicates whether the instance has rounded distances or not. The options are: [false, true]. The default value is true.

**-stoppingCriterion** : It is possible to use two different stopping criteria:
* **Time** : The algorithm stops when a given time in seconds has elapsed; 
* **Iteration** :  The algorithm stops when the given number of iterations has been reached. 

**-limit** : Refers to the value that will be used in the stopping criterion. If the stopping criterion is a time limit, this parameter is the timeout in seconds. Otherwise, this parameter indicates the number of iterations. The default value is the maximum limit for a double precision number in the JAVA language (Double.MAX_VALUE).

**-best** :  Indicates the value of the optimal solution. The default value is 0.

**-varphi** :  Parameter of the feasibility and local search methods that refers to the maximum cardinality of the set of nearest neighbors of the vertices. The default value is 40. The larger it is, the greater the number of movements under consideration in the methods. 

**-gamma** :  Number of iterations for AILS-II to perform a new adjustment of variable 𝜔. The default value is 30.

**-dMax** : Initial reference distance between the reference solution and the  solution obtained after the local search. The default value is 30.

**-dMin** : Final Reference distance between the reference solution and the solution obtained after the local search. The default value is 15.

**-warmStart** : (Optional) Path to a warm start solution file (.sol format). If provided, the algorithm will start from this solution instead of constructing one from scratch. If not provided, the algorithm will automatically look for a warm start file in `warm_start/<dataset>/<instance>.sol`.

**-solOutput** : (Optional) Path to save the output solution file. The algorithm saves the best solution every hour and at termination. If not provided, solutions are automatically saved to `solutions/<instance>.sol`.

## Warm Start Feature

The algorithm supports warm starting from a pre-computed solution. This can significantly improve solution quality when you have a good initial solution available.

### How It Works

1. **Auto-detection (default)**: If no `-warmStart` parameter is provided, the algorithm automatically looks for a solution file based on the instance path:
   * Instance: `data/XL/XL-n1048-k237.vrp`
   * Warm start: `warm_start/XL/XL-n1048-k237.sol`

2. **Manual path**: You can specify a custom warm start file using the `-warmStart` parameter.

3. **Fallback**: If no warm start file is found (either auto-detected or specified), the algorithm falls back to the construction heuristic with a clear log message.

### Solution File Format (.sol)

The warm start solution file should follow this format:

```text
Route #1: 103 360 681 121
Route #2: 999 212 931 676 374 361 934 919 245 604
Route #3: 637 570 975 137 349 130 378
...
Cost 380246.000000
```

* Each line starts with `Route #N:` followed by space-separated customer node IDs
* Node IDs are 1-indexed (depot node 0 is not included)
* The last line contains the total cost with the `Cost` keyword

### Sample Usage Commands

**Using auto-detected warm start:**

```console
java -jar AILSII.jar -file data/XL/XL-n1048-k237.vrp -rounded true -best 380246 -limit 100 -stoppingCriterion Time
```

**Using a specific warm start file:**

```console
java -jar AILSII.jar -file data/XL/XL-n1048-k237.vrp -warmStart warm_start/XL/XL-n1048-k237.sol -rounded true -best 380246 -limit 100 -stoppingCriterion Time
```

**Using a warm start file from a different location:**

```console
java -jar AILSII.jar -file data/XL/XL-n1048-k237.vrp -warmStart /path/to/my/solution.sol -rounded true -best 380246 -limit 100 -stoppingCriterion Time
```

### Log Output

The algorithm provides clear logging about warm start status:

**When warm start succeeds:**

```text
================================================================================
[WARM START] Loading warm start solution from: warm_start/XL/XL-n1048-k237.sol
[WARM START] SUCCESS: Loaded warm start solution with 239 routes, cost: 380246.0
================================================================================
```

**When warm start falls back to construction:**

```text
[WARM START] Warm start file not found: warm_start/XL/XL-n1048-k237.sol
================================================================================
[WARM START] FALLBACK: No warm start solution found. Using construction heuristic.
================================================================================
```

## Solution Output Feature

The algorithm automatically saves the best solution found during execution:

* **Hourly saves**: Every hour, the current best solution is saved to allow recovery from long runs
* **Final save**: At termination, the final best solution is always saved

### Output Path Resolution

1. **Auto-detection (default)**: If no `-solOutput` parameter is provided, solutions are saved to `solutions/<instance>.sol`
   * Instance: `data/XL/XL-n1048-k237.vrp`
   * Output: `solutions/XL-n1048-k237.sol`

2. **Manual path**: You can specify a custom output path using the `-solOutput` parameter

3. **Directory creation**: Parent directories are automatically created if they don't exist

### Solution Output Usage

**Using auto-detected output path:**

```console
java -jar AILSII.jar -file data/XL/XL-n1048-k237.vrp -rounded true -best 380246 -limit 7200 -stoppingCriterion Time
```

**Using a specific output path:**

```console
java -jar AILSII.jar -file data/XL/XL-n1048-k237.vrp -solOutput results/my_solution.sol -rounded true -best 380246 -limit 7200 -stoppingCriterion Time
```

### Solution Save Log Output

The algorithm logs when solutions are saved:

**Hourly save:**

```text
[SOLUTION SAVE] HOUR_1: Saved best solution (cost: 380500.0, K: 239) to: solutions/XL-n1048-k237.sol at time: 3600.0000s
```

**Final save at termination:**

```text
[SOLUTION SAVE] FINAL: Saved best solution (cost: 380246.0, K: 237) to: solutions/XL-n1048-k237.sol at time: 7200.0000s
```

## Data

The folder data contains all literature instances tested (files with extension .vrp). The files with the extension .sol refer to the Best Known Solutions (BKSs) used to calculate the gaps.

## Results

The folder results contain all tables and figures elaborated after carrying out the experiments using the instances found in the folder data. To achieve the results presented in [Table 2](results/Table2.png) and [Table 3 (part 1)](results/Table3_1.png), [Table 3 (part 2)](results/Table3_2.png) and [Table 3 (part 3)](results/Table3_3.png), we ran the scripts in folder [scripts](scripts). The script [scriptAilsIIUCHOA.sh](scripts/scriptAilsIIUCHOA.sh) refer to the tests performed with the X instances, whereas the script [scriptAilsIIArnold.sh](scripts/scriptAilsIIArnold.sh) run the remainder instances. 

