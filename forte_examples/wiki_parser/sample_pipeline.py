# Copyright 2019 The Forte Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import pickle
from tkinter import W
from typing import Dict, Optional

from forte.common.resources import Resources
from forte.data.data_pack import DataPack
from forte.datasets.wikipedia.dbpedia import (
    DBpediaWikiReader,
    WikiAnchorReader,
    WikiArticleWriter,
    WikiInfoBoxReader,
    WikiPropertyReader,
    WikiStructReader,
)
from forte.datasets.wikipedia.dbpedia.db_utils import load_redirects, print_progress
from forte.datasets.wikipedia.dbpedia.dbpedia_datasets import (
    WikiCategoryReader,
    WikiPackReader,
)
from forte.pipeline import Pipeline

from pirlib.iotypes import DirectoryPath
from pirlib.pipeline import pipeline as pir_pipeline
from pirlib.task import task


def add_wiki_info(
    reader: WikiPackReader,
    resources: Resources,
    wiki_info_data_path: str,
    input_pack_path: str,
    output_path: str,
    prompt_name: str,
    use_input_index=False,
    resume_from_last=False,
    input_index_file_path: Optional[str] = "article.idx",
    output_index_file_name: Optional[str] = "article.idx",
):
    """
    Add wiki resource into the data pack.

    Args:
        reader: The info reader that loads the data pack.
        resources: The resources object that should contain the redirects.
        wiki_info_data_path: The path containing the wiki data.
        input_pack_path: The initial data pack path.
        output_path: The resulting output path.
        prompt_name: a name to show during processing.
        use_input_index: whether to use the input index to determine the
          output path.
        resume_from_last: whether to resume from last end point.
        input_index_file_path: the full file path to the input index.
        output_index_file_name: the file path to write the output index,
            this is relative to `output_path`.

    Returns:

    """
    pl = Pipeline[DataPack](resources)

    out_index_path = os.path.join(output_path, output_index_file_name)

    if resume_from_last:
        if not os.path.exists(out_index_path):
            raise ValueError(
                f"Configured to do resume but path " f"{out_index_path} does not exists."
            )

        print_progress(f"\nWill resume from last from {out_index_path}", "\n")
        pl.set_reader(
            reader,
            config={
                "pack_index": input_index_file_path,
                "pack_dir": input_pack_path,
                "resume_index": out_index_path,
                "zip_pack": True,
            },
        )
    else:
        pl.set_reader(
            reader,
            config={
                "pack_index": input_index_file_path,
                "pack_dir": input_pack_path,
                "zip_pack": True,
            },
        )

    pl.add(
        WikiArticleWriter(),
        config={
            "output_dir": output_path,
            "zip_pack": True,
            "drop_record": True,
            "use_input_index": use_input_index,
            "input_index_file": input_index_file_path,
            "output_index_file": output_index_file_name,
            "append_to_index": resume_from_last,
        },
    )

    print_progress(f"Start running the {prompt_name} pipeline.", "\n")
    pl.run(wiki_info_data_path)
    print_progress(f"Done collecting {prompt_name}.", "\n")


def read_wiki_text(
    nif_context: str,
    output_dir: str,
    resources: Resources,
):

    pl = Pipeline[DataPack](resources)
    pl.set_reader(DBpediaWikiReader())
    pl.add(
        WikiArticleWriter(),
        config={
            "output_dir": output_dir,
            "zip_pack": True,
            "drop_record": True,
        },
    )
    print_progress("Start running wiki text pipeline.", "\n")
    pl.run(nif_context)
    print_progress("Done collecting wiki text.", "\n")


def cache_redirects(base_output_path: str, redirect_path: str) -> Dict[str, str]:
    redirect_pickle = os.path.join(base_output_path, "redirects.pickle")

    redirect_map: Dict[str, str]
    if os.path.exists(redirect_pickle):
        redirect_map = pickle.load(open(redirect_pickle, "rb"))
    else:
        redirect_map = load_redirects(redirect_path)
        with open(redirect_pickle, "wb") as pickle_f:
            pickle.dump(redirect_map, pickle_f)
    return redirect_map


def get_path(base_dir: DirectoryPath, dataset: str):
    p = base_dir / dataset
    if p.exists():
        return str(p)
    else:
        raise FileNotFoundError(
            f"The dataset {dataset} is not found in " f"base directory {base_dir}"
        )


@task
def read_wiki_task(base_input_dir: DirectoryPath) -> DirectoryPath:
    base_output_dir = task.context().output
    redirects = get_path(base_input_dir, "redirects.tql")
    nif_context = get_path(base_input_dir, "nif_context.tql")

    base_output_dir = str(base_output_dir)
    # The datasets are read in a few steps.
    # Load redirects between wikipedia pages.
    print_progress("Loading redirects", "\n")

    redirect_map: Dict[str, str] = cache_redirects(base_output_dir, redirects)

    resources: Resources = Resources()
    resources.update(redirects=redirect_map)
    print_progress("Done loading.", "\n")

    # Read the wiki text.
    raw_pack_dir = str(base_output_dir)
    read_wiki_text(nif_context, raw_pack_dir, resources, True)
    print_progress("Done reading wikipedia text.", "\n")
    return DirectoryPath(base_output_dir)


@task
def add_struct_info(base_input_dir: DirectoryPath, raw_pack_dir: DirectoryPath) -> DirectoryPath:
    output_dir = task.context().output
    redirects = get_path(base_input_dir, "redirects.tql")
    raw_pack_dir = str(raw_pack_dir)

    nif_page_structure = get_path(base_input_dir, "nif_page_structure.tql")
    struct_dir = str(output_dir)

    redirect_map: Dict[str, str] = cache_redirects(str(raw_pack_dir), redirects)

    resources: Resources = Resources()
    resources.update(redirects=redirect_map)

    main_index = os.path.join(raw_pack_dir, "article.idx")

    add_wiki_info(
        WikiStructReader(),
        resources,
        nif_page_structure,
        raw_pack_dir,
        struct_dir,
        "page_structures",
        use_input_index=True,
        resume_from_last=False,
        input_index_file_path=main_index,
    )

    return output_dir


@task
def add_link_info(
    base_input_dir: DirectoryPath,
    raw_pack_dir: DirectoryPath,
    struct_dir: DirectoryPath,
) -> DirectoryPath:
    output_dir = task.context().output
    redirects = get_path(base_input_dir, "redirects.tql")
    nif_text_links = get_path(base_input_dir, "text_links.tql")

    struct_dir = str(struct_dir)
    link_dir = str(output_dir)

    redirect_map: Dict[str, str] = cache_redirects(str(raw_pack_dir), redirects)

    resources: Resources = Resources()
    resources.update(redirects=redirect_map)

    main_index = os.path.join(raw_pack_dir, "article.idx")

    add_wiki_info(
        WikiAnchorReader(),
        resources,
        nif_text_links,
        struct_dir,
        link_dir,
        "anchor_links",
        use_input_index=True,
        resume_from_last=False,
        input_index_file_path=main_index,
    )
    return output_dir


@task
def add_property_info(
    base_input_dir: DirectoryPath,
    raw_pack_dir: DirectoryPath,
    link_dir: DirectoryPath,
) -> DirectoryPath:
    output_dir = task.context().output
    redirects = get_path(base_input_dir, "redirects.tql")
    info_boxs_properties = get_path(base_input_dir, "infobox_properties_mapped_en.tql")

    link_dir = str(link_dir)
    property_dir = str(output_dir)

    redirect_map: Dict[str, str] = cache_redirects(str(raw_pack_dir), redirects)

    resources: Resources = Resources()
    resources.update(redirects=redirect_map)

    main_index = os.path.join(raw_pack_dir, "article.idx")

    add_wiki_info(
        WikiPropertyReader(),
        resources,
        info_boxs_properties,
        link_dir,
        property_dir,
        "info_box_properties",
        use_input_index=True,
        resume_from_last=False,
        output_index_file_name="properties.idx",
        input_index_file_path=main_index,
    )
    return output_dir


@task
def add_literal_info(
    base_input_dir: DirectoryPath,
    raw_pack_dir: DirectoryPath,
    property_dir: DirectoryPath,
) -> DirectoryPath:
    output_dir = task.context().output
    redirects = get_path(base_input_dir, "redirects.tql")
    mapping_literals = get_path(base_input_dir, "literals.tql")

    property_dir = str(property_dir)
    literal_dir = str(output_dir)

    redirect_map: Dict[str, str] = cache_redirects(str(raw_pack_dir), redirects)

    resources: Resources = Resources()
    resources.update(redirects=redirect_map)

    main_index = os.path.join(raw_pack_dir, "article.idx")

    add_wiki_info(
        WikiInfoBoxReader(),
        resources,
        mapping_literals,
        property_dir,
        literal_dir,
        "literals",
        use_input_index=True,
        resume_from_last=False,
        output_index_file_name="literals.idx",
        input_index_file_path=main_index,
    )
    return DirectoryPath(literal_dir)


@task
def add_object_info(
    base_input_dir: DirectoryPath,
    raw_pack_dir: DirectoryPath,
    literal_dir: DirectoryPath,
) -> DirectoryPath:
    output_dir = task.context().output
    redirects = get_path(base_input_dir, "redirects.tql")
    mapping_objects = get_path(base_input_dir, "mappingbased_objects_en.tql")

    literal_dir = str(literal_dir)
    mapping_dir = str(output_dir)

    redirect_map: Dict[str, str] = cache_redirects(str(raw_pack_dir), redirects)

    resources: Resources = Resources()
    resources.update(redirects=redirect_map)

    main_index = os.path.join(raw_pack_dir, "article.idx")

    add_wiki_info(
        WikiInfoBoxReader(),
        resources,
        mapping_objects,
        literal_dir,
        mapping_dir,
        "objects",
        use_input_index=True,
        resume_from_last=False,
        output_index_file_name="objects.idx",
        input_index_file_path=main_index,
    )
    return output_dir


@task
def add_category_info(
    base_input_dir: DirectoryPath,
    raw_pack_dir: DirectoryPath,
    mapping_dir: DirectoryPath,
) -> DirectoryPath:
    output_dir = task.context().output
    redirects = get_path(base_input_dir, "redirects.tql")
    categories = get_path(base_input_dir, "article_categories_en.tql")

    mapping_dir = str(mapping_dir)
    category_dir = output_dir

    redirect_map: Dict[str, str] = cache_redirects(str(raw_pack_dir), redirects)

    resources: Resources = Resources()
    resources.update(redirects=redirect_map)

    main_index = os.path.join(raw_pack_dir, "article.idx")

    add_wiki_info(
        WikiCategoryReader(),
        resources,
        categories,
        mapping_dir,
        category_dir,
        "categories",
        use_input_index=True,
        resume_from_last=False,
        output_index_file_name="categories.idx",
        input_index_file_path=main_index,
    )
    return output_dir


@pir_pipeline
def sample_pipeline(input_dir: DirectoryPath) -> DirectoryPath:
    raw_pack_dir = read_wiki_task(input_dir)
    return add_category_info(
        input_dir,
        raw_pack_dir,
        add_object_info(
            input_dir,
            raw_pack_dir,
            add_literal_info(
                input_dir,
                raw_pack_dir,
                add_property_info(
                    input_dir,
                    raw_pack_dir,
                    add_link_info(
                        input_dir, raw_pack_dir, add_struct_info(input_dir, raw_pack_dir)
                    ),
                ),
            ),
        ),
    )
