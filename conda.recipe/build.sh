$PYTHON setup.py install

paths=("HydroBasins/level_one" "HydroBasins/level_twelve" "DEM/MERIT103" \
       "DEM/MERIT_FDR" "DEM/MERIT_UDA" "DEM/MERIT_ELEV_HP" "DEM/MERIT_WTH")

if [ "$(uname)" == "Darwin" ]; then
    datapath = "$HOME/Library/Application Support/rabpro"
fi

if [ "$(uname)" == "Linux" ]; then
    datapath = "$XDG_DATA_HOME/rabpro"
fi

mkdir -p "$datapath"

for p in ${paths[@]}; do
    mkdir -p "${datapath}/${p}"
done
